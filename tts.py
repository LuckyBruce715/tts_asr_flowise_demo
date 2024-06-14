# -*- coding: utf-8 -*-

from huaweicloud_sis.client.tts_client import TtsCustomizationClient
from huaweicloud_sis.bean.tts_request import TtsCustomRequest
from huaweicloud_sis.bean.sis_config import SisConfig
from huaweicloud_sis.exception.exceptions import ClientException
from huaweicloud_sis.exception.exceptions import ServerException
import json


def ttsc_example():
    """ 语音合成demo """
    ak = '31IS7I1OTHTVOOENE5MU'            # 你的AK
    sk = 'qw6W51SMlVHelkQyxyJ0lDl0c2HxDFPG2d3R9XnB'            # 你的SK
    region = 'cn-north-4'    # 你的Region，例如：cn-north-4
    project_id = '0cc79931ce00f34f2f8cc017c3dafc58'  # 你的Project ID
    text = '你好，我是露西'    # 待合成文本，不超过500字
    path = 'C:/users/bruce/downloads/test.wav'  # 保存路径

    # step1 初始化客户端
    config = SisConfig()
    config.set_connect_timeout(10)       # 设置连接超时，单位s
    config.set_read_timeout(10)          # 设置读取超时，单位s
    # 如果需要使用代理，请取消下面的注释并配置代理
    # config.set_proxy(proxy)
    ttsc_client = TtsCustomizationClient(ak, sk, region, project_id, sis_config=config)

    # step2 构造请求
    ttsc_request = TtsCustomRequest(text)
    # 设置请求参数
    ttsc_request.set_property('chinese_huaxiaowen_common')
    ttsc_request.set_audio_format('wav')
    ttsc_request.set_sample_rate('8000')
    ttsc_request.set_volume(50)
    ttsc_request.set_pitch(0)
    ttsc_request.set_speed(0)
    ttsc_request.set_saved(True)
    ttsc_request.set_saved_path(path)

    # step3 发送请求，返回结果。如果设置保存，可在指定路径里查看保存的音频。
    result = ttsc_client.get_ttsc_response(ttsc_request)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        ttsc_example()
    except ClientException as e:
        print(f"ClientException: {e}")
    except ServerException as e:
        print(f"ServerException: {e}")