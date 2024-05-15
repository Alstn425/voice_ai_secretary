import concurrent.futures
import textwrap
import requests
import webbrowser
import folium
from IPython.display import Markdown
import speech_recognition as sr
import openai
from weather_desc import weather_desc_ko
from elevenlabs import Voice, VoiceSettings, play
from elevenlabs.client import ElevenLabs


# OpenAI API 키 설정
openai_api_key = "사서 쓰십시오"

# API 키 설정
api_key = "발급 받아서 쓰십시오"
openweathermap_api_key = "발급 받아서 쓰십시오"

# 서식이 지정된 Markdown 텍스트를 표시하는 함수
def to_markdown(text):
    text = text.replace('•', ' *')
    return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))


def tts_with_elevenlabs(text):
    client = ElevenLabs(api_key="사서 쓰십시오")
    audio = client.generate(
        text=text,
        model="eleven_multilingual_v2",
        voice=Voice(
            voice_id='사서 쓰십시오',
            settings=VoiceSettings(stability=0.71, similarity_boost=0.7, style=0.0, use_speaker_boost=True)
        )
    )
    play(audio)



def tts_with_elevenlabs_async(text):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(tts_with_elevenlabs, text)
        return_value = future.result()


def get_location(api_key, address):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    if data["status"] == "OK":
        location = data["results"][0]["geometry"]["location"]
        latitude = location["lat"]
        longitude = location["lng"]
        return latitude, longitude
    else:
        print("Failed to retrieve location data.")
        return None


def get_weather(api_key, latitude, longitude):
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={api_key}&units=metric&lang=kr"
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200:
        weather_code = data['weather'][0]['id']
        weather_description = weather_desc_ko.get(weather_code, '알 수 없는 날씨')
        temperature = data['main']['temp']
        return weather_description, temperature
    else:
        print("Failed to retrieve weather data.")
        return None, None


def show_map(latitude, longitude):
    map_obj = folium.Map(location=[latitude, longitude], zoom_start=15)
    folium.Marker([latitude, longitude], popup='Your Location').add_to(map_obj)
    map_obj.save('map.html')
    webbrowser.open('map.html')


def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("말하세요...")
        audio = recognizer.listen(source)
    try:
        print("음성 인식 중...")
        query = recognizer.recognize_google(audio, language="ko-KR")
        print("인식된 텍스트:", query)
        return query
    except sr.UnknownValueError:
        print("음성을 인식할 수 없습니다.")
        return ""
    except sr.RequestError:
        print("인식 서비스에 접근할 수 없습니다.")
        return ""

# OpenAI 챗GPT 모델 초기화
openai.api_key = openai_api_key
chat_model = "gpt-3.5-turbo-0125"  # 여기에 사용하려는 모델의 이름을 입력하세요

# 대화 시작
talking_mode = False
current_question = ""
while True:
    q = recognize_speech()
    if not q:
        continue

    if q == "대화 종료":
        print("\n대화를 종료합니다.")
        tts_with_elevenlabs("대화를 종료합니다.")
        break

    if "박기환" in q.lower():
        talking_mode = True
        current_question = q.split("박기환")[1].strip()
        continue

    if '위치 보여 줘' in q or '위치 알려 줘' in q:
        location_query = q.replace("위치 보여 줘", "").replace("위치 알려 줘", "").strip()
        location = get_location(api_key, location_query)
        if location:
            show_map(location[0], location[1])
            print(f"{location_query}의 지도를 표시합니다.")
            tts_with_elevenlabs_async(f"{location_query}의 지도를 표시합니다.")
        else:
            print(f"{location_query}의 위치 정보를 가져올 수 없습니다.")
            tts_with_elevenlabs_async(f"{location_query}의 위치 정보를 가져올 수 없습니다.")
        continue

    if '날씨 알려 줘' in q:
        location_query = q.replace("날씨 알려 줘", "").strip()
        location = get_location(api_key, location_query)
        if location:
            weather_description, temperature = get_weather(openweathermap_api_key, location[0], location[1])
            if weather_description and temperature:
                print(f"{location_query}의 날씨는 {weather_description}이며, 온도는 {temperature}°C입니다.")
                tts_with_elevenlabs_async(f"{location_query}의 날씨는 {weather_description}이며, 온도는 {temperature}도입니다.")
            else:
                print(f"{location_query}의 날씨 정보를 가져올 수 없습니다.")
                tts_with_elevenlabs_async(f"{location_query}의 날씨 정보를 가져올 수 없습니다.")
        else:
            print(f"{location_query}의 위치 정보를 가져올 수 없습니다.")
            tts_with_elevenlabs_async(f"{location_query}의 위치 정보를 가져올 수 없습니다.")
        continue

     # 말하기 모드일 때
    if talking_mode:
        # 질문 처리 및 답변
        current_question += " " + q  # 이전 질문에 현재 인식된 텍스트 추가
        response = openai.ChatCompletion.create(model=chat_model, messages=[{"role": "system", "content": "당신은 '박민수'님과 '김상민'님께서 만드신 음성 인공지능 비서 ‘박기환’입니다. 당신은 대화하는 사용자에게 존댓말을 써야합니다. 당신의 대답은 간결해야 합니다."}, {"role": "user", "content": current_question}])   
        gpt_response = response.choices[0].message['content']
        print("\n챗 GPT의 답변:", gpt_response)
        # GPT의 응답을 ElevenLabs API를 통해 TTS로 변환하여 재생
        tts_with_elevenlabs(gpt_response)
        # 다음 질문 초기화
        current_question = ""