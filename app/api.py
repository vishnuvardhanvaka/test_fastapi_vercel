from fastapi import FastAPI,Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
import google.generativeai as genai
from datetime import datetime
from pymongo import MongoClient,DESCENDING
from datetime import datetime,timedelta


origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost:3000",
    "http://localhost:3000/",
    "http://192.168.0.128:3000/",
    "https://miraparentpal.com",
    "https://www.miraparentpal.com",
    'https://miraparentpal.vercel.app',
    'https://inotes-gamma.vercel.app',
    'https://ai-avatar-live-stream.vercel.app'
]

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import subprocess
import threading

class StreamProcess:
    def __init__(self, video_path, stream_key):
        self.video_path = video_path
        self.stream_key = stream_key
        self.process = None
        self.stop_event = threading.Event()

    def start(self):
        args = [
          '-stream_loop', '-1',
          '-re',
          '-i', self.video_path,
          '-c', 'copy',
          '-b:v', '6800k',  # Set the video bitrate to 6800 Kbps
          '-f', 'flv',
          '-fflags', 'nobuffer',
          '-flags', 'low_delay',
          f'rtmp://a.rtmp.youtube.com/live2/{self.stream_key}'
      ]

        self.process = subprocess.Popen(['ffmpeg'] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    def check_stream(self):
      if self.process and self.process.poll() is None:
        # print("Streaming process running")
        return True
      # print("Streaming process stopped")
      return False
    def stop(self):
        if self.process and self.process.poll() is None:
            self.stop_event.set()  # Signal the thread to stop
            self.process.terminate()  # Terminate the ffmpeg process

def stream_video(video_path, stream_key):
    stream_process = StreamProcess(video_path, stream_key)
    stream_thread = threading.Thread(target=stream_process.start)
    stream_thread.start()
    return stream_process

stream_process = None

@app.get('/startStreaming')
async def startStreaming():
    global stream_process
    # video_path='./finalVideo.mp4'
    video_path = './finalVideo.mp4'
    stream_key='68p2-txmk-79sm-hjfh-2d26'
    stream_process = stream_video(video_path,stream_key)
    return {"stream_status":stream_process.check_stream()}

@app.get('/stopStreaming')
async def stopStreaming():
    global stream_process
    if stream_process:
        stream_process.stop()
    return {"stream_status":stream_process.check_stream()}


class Database:
  def __init__(self):
    connection_url='mongodb+srv://infospherecom:vishnu1$@infosphere.ijmwdnx.mongodb.net/'
    # print(connection_url)
    client=MongoClient(connection_url)
    #print('Client connection successful !')
    self.database=client.infosphere
    self.user_collection=self.database.userdata
    self.news_collection=self.database.newsCollection
    print('Successfully connected to the database !')
  def save_news(self, document):
    existing_document = self.news_collection.find_one({"headline": document["headline"]})
    if existing_document:
        return {'success': False, 'message': 'Headline already exists in the database'}
    else:
        id = self.news_collection.insert_one(document)
        return {'success': True, 'message': 'News saved successfully'}

  def save_sports_indian_express_news(self, document):
    existing_document = self.news_collection.find_one({"headline": document["headline"]})
    if existing_document:
        return {'success': False, 'message': 'Headline already exists in the database'}
    else:
        id = self.news_collection.insert_one(document)
        return {'success': True, 'message': 'News saved successfully'}

  def getNews(self, category=None, date=None, end_date=None):
    query = {}
    if category:
        query["category"] = category
    if date:
        date_object = datetime.strptime(date, "%Y-%m-%d")
        query["datetime"] = {"$gte": date_object, "$lt": date_object + timedelta(days=1)}

    if not (category or date or end_date):
        # No filters provided, retrieve all news articles sorted by datetime in descending order
        news_articles = self.news_collection.find().sort("datetime", DESCENDING)
    else:
      news_articles = self.news_collection.find(query).sort("datetime", DESCENDING)
    news=[]
    for article in news_articles:
        # print(article)
        article.pop('_id', None)
        news.append(article)
    return news
db=Database()


#Programmable Search Engine
API_KEY='AIzaSyD_kA4vs7IGC9LGlQf1KzoPAaMdork5L6U'
CSE_ID='e643ba6afdcd842cf'
service = build("customsearch", "v1", developerKey=API_KEY)
def search_images(query, num=1):
    res = service.cse().list(
        q=query,
        cx=CSE_ID,
        searchType="image",
        num=num
    ).execute()
    return res.get("items", [])

def summarize(headline,content):
  GOOGLE_API_KEY='AIzaSyAU_L_qPbG-7fzYuFOt5YGmTN8IONx2hwI'
  genai.configure(api_key=GOOGLE_API_KEY)
  # for models in genai.list_models():
  #   if 'generateContent' in models.supported_generation_methods:
  #     print(models.name)
  generation_config = {
    "candidate_count": 1,
    "max_output_tokens": 256,
    "temperature": 1.0,
    "top_p": 0.7,
  }

  safety_settings=[
    {
      "category": "HARM_CATEGORY_DANGEROUS",
      "threshold": "BLOCK_NONE",
    },
    {
      "category": "HARM_CATEGORY_HARASSMENT",
      "threshold": "BLOCK_NONE",
    },
    {
      "category": "HARM_CATEGORY_HATE_SPEECH",
      "threshold": "BLOCK_NONE",
    },
    {
      "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
      "threshold": "BLOCK_NONE",
    },
    {
      "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
      "threshold": "BLOCK_NONE",
    },
  ]

  model = genai.GenerativeModel(
      model_name="gemini-pro",
      generation_config=generation_config,
      safety_settings=safety_settings
  )
  # model = genai.GenerativeModel('gemini-pro')
  # model = genai.GenerativeModel('gemini-1.0-pro-latest')
  prompt_summary=f'''Summarize this below news content to major points.
    NEWS_CONTENT: "{content}"
    <<<Note: Don't put any '*' or '-' in the points. Just put a '\n' between the points>>>
    '''
  summary = model.generate_content(prompt_summary).text
#   print(summary.text)

  prompt_title=f'''Below is the news content, give a eye catching title.
    HEADLINE:"{headline}"
    NEWS_CONTENT: "{content}"
    <<<Note: Don't put any '*' or '-' in the title.>>>
    '''
  title = model.generate_content(prompt_title).text
#   print(title)
  return title,summary



def formate_date(date):
  date_string = "01 Mar, 2024, 23:59 ET"

  input_format = "%d %b, %Y, %H:%M ET"

  date_object = datetime.strptime(date, input_format)

  database_format = "%Y-%m-%d %H:%M:%S"
  formated_date = date_object.strftime(database_format)
  return formated_date


def prNewsWire(category=''):
  
  root_url= 'https://www.prnewswire.com'
  if category=='':
    list_url= 'https://www.prnewswire.com/news-releases/news-releases-list/?page=1&pagesize=200'
  elif category=='automotive':
    list_url='https://www.prnewswire.com/news-releases/automotive-transportation-latest-news/automotive-transportation-latest-news-list/?page=1&pagesize=200'
  elif category=='business':
    list_url='https://www.prnewswire.com/news-releases/business-technology-latest-news/business-technology-latest-news-list/?page=1&pagesize=200'
  elif category=='media':
    list_url='https://www.prnewswire.com/news-releases/entertainment-media-latest-news/entertainment-media-latest-news-list/?page=1&pagesize=200'
  elif category=='financial':
    list_url='https://www.prnewswire.com/news-releases/financial-services-latest-news/financial-services-latest-news-list/?page=1&pagesize=200'
  elif category=='general-business':
    list_url='https://www.prnewswire.com/news-releases/general-business-latest-news/general-business-latest-news-list/?page=1&pagesize=200'
  elif category=='consumer-technologies':
    list_url='https://www.prnewswire.com/news-releases/consumer-technology-latest-news/consumer-technology-latest-news-list/?page=1&pagesize=200'
  elif category=='natural-resources':
    list_url='https://www.prnewswire.com/news-releases/energy-latest-news/energy-latest-news-list/?page=1&pagesize=200'
  elif category=='environment':
    list_url='https://www.prnewswire.com/news-releases/environment-latest-news/environment-latest-news-list/?page=1&pagesize=200'
  elif category=='industry':
    list_url='https://www.prnewswire.com/news-releases/heavy-industry-manufacturing-latest-news/heavy-industry-manufacturing-latest-news-list/?page=1&pagesize=200'
  elif category=='telecommunication':
    list_url='https://www.prnewswire.com/news-releases/telecommunications-latest-news/telecommunications-latest-news-list/?page=1&pagesize=200'
  elif category=='food':
    list_url='https://www.prnewswire.com/news-releases/consumer-products-retail-latest-news/food-beverages-list/?page=1&pagesize=200'
  elif category=='health':
    list_url='https://www.prnewswire.com/news-releases/health-latest-news/health-latest-news-list/?page=1&pagesize=200'


  response = requests.get(list_url)
  soup = BeautifulSoup(response.content, 'html.parser')

  main_class = soup.find_all(class_='row newsCards')
  anchor_tags = soup.find_all('a', class_='newsreleaseconsolidatelink display-outline w-100')
  
  news_links={}
  for anchor_tag in anchor_tags:
      span_element = anchor_tag.find('span', class_='langspan')
      if span_element:
          lang_value = str(span_element.get('lang'))

      else:
        lang_value='en'
        final_url=root_url+str(anchor_tag.get('href'))
        news_links[final_url]=lang_value
#   print(news_links)

  print(f'Number of pr news updates : {len(news_links)}')

  news_data=[]
  count=1
  for news_link in news_links:
    if count==3:
      break
    # print(count, news_link)

    response = requests.get(news_link)
    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")

    time_class=soup.find("p",class_='mb-no')
    date_time=time_class.text
    date_time=formate_date(date_time)
    date_object = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
    # print(date_time,'99999999',date_time,date_object,type(date_object))
    
    figure_tag = soup.find("figure")
    # print(figure_tag)
    heading_class = soup.find(class_='row detail-headline')
    headline_text=heading_class.get_text().strip()
    # print(headline_text)

    if figure_tag != None:
      a_tag = figure_tag.find("a")
      img_tag = a_tag.find("img")
      img_url=img_tag.get('data-getimg')
      if img_url==None:
        img_url=img_tag.get('src')
      if ".mp4" in str(img_url):
        img_url = img_url.split(".mp4")[0] + ".mp4"
      # print(img_url)
    else:
      result = search_images(headline_text)
      for img in result:
        img_url=img["link"]
      
    
    all_p_tags = soup.find_all(["i","p","strong"])
    content=''
    for p_tag in all_p_tags:
        content+=p_tag.get_text()+'\n'
    content=f'News Headline: {headline_text}'+'\n\n'+content.strip()
    remove_words=['In-Language News','Searching for your content...','Share this article','Contact Us',' 888-776-0942','from 8 AM - 10 PM ET','\n\n\n\n','No results found. Please change your search terms and try again.']
    for word in remove_words:
      content=content.replace(word,'').strip()

    # print(headline_text)
    # print(img_url)
    # print(content)

    title,points=summarize(headline_text,content)
    # print(title)
    # print(img_url)
    # print(points)
    document = {
        'category':category,
        'datetime':date_object,
        'headline':headline_text,
        'title':title,
        'img_url':img_url,
        'points':points
    }
    # status=db.save_news(document)
    # print(status)
    news_data.append(document)
    print('saved to db ---------------------------------------------')


    # title,summary_data=modelling.summarize(content)
    # print('------------------------------\n title: ',title,'\n',summary_data,'\n  -------------------------------------------------')
    # news_summaries[title]=summary_data
    count+=1
  return news_data
# pr_news_data=prNewsWire('food')
# print(pr_news_data)
# email:str=Form(...)

@app.post('/getNews/')
async def getNews(category: Optional[str] = Form(None), date: Optional[str] = Form(None)):
    print(category, date, type(category), type(date))
    if category=='null':
       category=None
    if date=='null':
       date=None
    news_articles = db.getNews(category=category, date=date)
    return {'news_articles': news_articles}

@app.get('/',tags=['Root'])
async def hello():
    return {'success':'you have successfully deployed fastapi to vercel'}




