import os
import json
import requests
import asyncio
from pydub import AudioSegment
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from huaweicloud_sis.client.rasr_client import RasrClient
from huaweicloud_sis.bean.rasr_request import RasrRequest
from huaweicloud_sis.bean.callback import RasrCallBack
from huaweicloud_sis.bean.sis_config import SisConfig
from huaweicloud_sis.client.tts_client import TtsCustomizationClient
from huaweicloud_sis.bean.tts_request import TtsCustomRequest
from io import BytesIO

app = FastAPI()

# 启用CORS
origins = ["http://localhost", "https://120.46.192.158", "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置环境变量或直接使用字符串
ak = os.getenv("HUAWEICLOUD_SIS_AK", '31IS7I1OTHTVOOENE5MU')
sk = os.getenv("HUAWEICLOUD_SIS_SK", 'qw6W51SMlVHelkQyxyJ0lDl0c2HxDFPG2d3R9XnB')
project_id = '0cc79931ce00f34f2f8cc017c3dafc58'
region = 'cn-north-4'
audio_format = 'pcm16k16bit'
model_property = 'chinese_16k_general'

class StreamHandler:
    def __init__(self):
        self.websocket = None
        self.buffer = BytesIO()

    def set_websocket(self, websocket):
        self.websocket = websocket

    async def on_response(self, message):
        result = json.loads(message)
        await self.websocket.send_text(json.dumps(result))

stream_handler = StreamHandler()

class MyCallback(RasrCallBack):
    def __init__(self):
        self.full_text = []

    def on_open(self):
        print('websocket connect success')

    def on_start(self, message):
        print('websocket start to recognize, %s' % message)

    async def send_tts_response(self, tts_response):
        print('Sending TTS response...')
        await stream_handler.websocket.send_bytes(tts_response)
        print('TTS response sent.')

    def on_response(self, message):
        try:
            if isinstance(message, dict):
                response = message
            else:
                response = json.loads(message)

            segments = response.get('segments', [])
            for segment in segments:
                text = segment['result'].get('text', '')
                is_final = segment.get('is_final', False)

                if is_final:
                    self.full_text.append(text)
                    combined_text = ''.join(self.full_text)
                    print("Combined Text: ", combined_text)
                    # 调用大模型API
                    payload = {"question": combined_text,"overrideConfig": {
        			"sessionId": "6f184bf4-0932-4abd-bd29-68a2756be3a4"
    		    }}
                    response = query(payload)
                    print("API Response: ", response)

                    # 调用TTS服务
                    tts_response = tts_service(response['text'])
                    print('TTS response generated.')
                    asyncio.run(self.send_tts_response(tts_response))

                print("response message:", segment)

        except json.JSONDecodeError:
            print("Error parsing message:", message)

    def on_end(self, message):
        print('websocket is ended!!!!, %s' % message)

    def on_close(self):
        print('websocket is closed!!!!')

    def on_error(self, error):
        print(error)

    def on_event(self, event):
        print(event)

def query(payload):
    API_URL = "https://ai.luckybruce.com/api/v1/prediction/f6d6df35-0934-4603-a1ef-9c197e5ae3d8"
    response = requests.post(API_URL, json=payload)
    return response.json()

def tts_service(text):
    config = SisConfig()
    config.set_connect_timeout(10)
    config.set_read_timeout(10)
    tts_client = TtsCustomizationClient(ak, sk, region, project_id, sis_config=config)

    tts_request = TtsCustomRequest(text)
    tts_request.set_property('chinese_huaxiaowen_common')
    tts_request.set_audio_format('wav')
    tts_request.set_sample_rate('8000')
    tts_request.set_volume(50)
    tts_request.set_pitch(0)
    tts_request.set_speed(0)
    tts_request.set_saved(False)  # 不保存到文件

    result = tts_client.get_ttsc_response(tts_request)
    audio_data = result['result']['data']
    if not audio_data:
        raise ValueError("No audio data received from TTS service.")
    
    # 保存音频数据到本地文件
    with open('test_audio.wav', 'wb') as f:
        f.write(audio_data)
    
    # 使用pydub检查音频格式
    audio_segment = AudioSegment.from_wav(BytesIO(audio_data))
    print(f"Channels: {audio_segment.channels}")
    print(f"Frame rate: {audio_segment.frame_rate}")
    print(f"Sample width: {audio_segment.sample_width}")

    return audio_data

@app.websocket("/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    stream_handler.set_websocket(websocket)

    config = SisConfig()
    config.set_connect_timeout(15)
    config.set_read_timeout(15)
    config.set_connect_lost_timeout(15)

    rasr_client = RasrClient(
        ak=ak,
        sk=sk,
        use_aksk=True,
        region=region,
        project_id=project_id,
        callback=MyCallback(),
        config=config
    )

    try:
        request = RasrRequest(audio_format, model_property)
        request.set_add_punc('yes')
        request.set_vad_head(10000)
        request.set_vad_tail(500)
        request.set_max_seconds(30)
        request.set_interim_results('yes')
        request.set_digit_norm('yes')
        request.set_need_word_info('yes')

        rasr_client.continue_stream_connect(request)
        rasr_client.send_start()

        print('Sent START message')

        while True:
            data = await websocket.receive_bytes()
            if not data:
                break

            stream_handler.buffer.write(data)
            stream_handler.buffer.seek(0)

            try:
                rasr_client.send_audio(stream_handler.buffer.read())
            except Exception as e:
                print(f'Error sending audio: {e}')
                break

            stream_handler.buffer.seek(0)
            stream_handler.buffer.truncate(0)

        rasr_client.send_end()
        print('Sent END message')
    except Exception as e:
        print(f"RASR error: {e}")
    finally:
        try:
            rasr_client.close()
            print("RASR client successfully closed.")
        except AttributeError as e:
            if 'isAlive' in str(e):
                print("Encountered 'isAlive' AttributeError, ensure you are using Python 3 where it should be 'is_alive()'.")
            else:
                raise
        except Exception as e:
            print(f"Error while closing RASR client: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000, ssl_certfile='/root/ssl/cert.pem', ssl_keyfile='/root/ssl/private.key')

