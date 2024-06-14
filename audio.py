import asyncio
import ssl
import websockets
import pyaudio

# WebSocket服务器的URL
WS_SERVER = "wss://120.46.192.158:9000/audio"

# 配置音频流
FORMAT = pyaudio.paInt16  # 根据实际的采样格式设置
CHANNELS = 1              # 根据实际的通道数设置
RATE = 16000              # 根据实际的采样率设置
CHUNK = 1024

ssl_context = ssl._create_unverified_context()

async def send_audio():
    async with websockets.connect(WS_SERVER, ssl=ssl_context) as websocket:
        # 初始化PyAudio
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

        print("Recording and streaming...")

        async def receive_audio():
            audio_play = pyaudio.PyAudio()
            stream_play = audio_play.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

            try:
                while True:
                    data = await websocket.recv()
                    if isinstance(data, bytes):
                        #print("Received audio data of length:", len(data))
                        stream_play.write(data)
                    else:
                        print("Received non-audio data")
            except websockets.ConnectionClosed:
                print("Connection with server closed")
            finally:
                stream_play.stop_stream()
                stream_play.close()
                audio_play.terminate()

        try:
            receive_task = asyncio.create_task(receive_audio())
            while True:
                data = stream.read(CHUNK, exception_on_overflow=False)
                print(f"Sending audio data of length: {len(data)}")
                await websocket.send(data)

        except websockets.ConnectionClosed:
            print("Connection with server closed")
        finally:
            receive_task.cancel()
            stream.stop_stream()
            stream.close()
            audio.terminate()

# 运行协程
asyncio.get_event_loop().run_until_complete(send_audio())
