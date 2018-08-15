#! python3
import sys
import time
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineQueryResultArticle, InputTextMessageContent
from pprint import pprint
import re
import requests
import json
import urllib
import urllib.request
from bs4 import BeautifulSoup
import datetime
from emoji import emojize

import pymongo
from pymongo import MongoClient


APITOKEN = "<API-TOKEN>"
bot = telepot.Bot(APITOKEN)
answerer = telepot.helper.Answerer(bot)

BASE = 'http://www.app.neaea.gov.et'

connection_params = {
    'user': '<USERNAME>',
    'password': '<PASSWORD>',
    'host': '<example.mlab.com>',
    'port': 777,
    'namespace': '<DATABASE-NAME>',
}

connection = MongoClient(
    'mongodb://{user}:{password}@{host}:'
    '{port}/{namespace}'.format(**connection_params)
)

db = connection.neaea

userMsg = db.messages
errors = db.errors
botResponse = db.response

#You should probably update the cookies to a newer one
cookies = {
    'ASP.NET_SessionId': 'ddsquu0ors1ezougotntgj2s',
    '__RequestVerificationToken': 'BtGOv0w_6CbHUc4M7rqYffbPYmeTAVWVxv82X7nZYtm5y7DvvHMDpdT-yRq3jk-ZMDLWx67vRGLHcHGr8rIBQXLlA6150_we8s47oLinfu81',
    '_ga': 'GA1.3.1681415141.1533025371',
    '_gid': 'GA1.3.2115169709.1533025371',
    '_gat': '1',
}

headers = {
    'Origin': 'http://www.app.neaea.gov.et',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Accept': '*/*',
    'Referer': 'http://www.app.neaea.gov.et/Home/Student',
    'X-Requested-With': 'XMLHttpRequest',
    'Connection': 'keep-alive',
}

def handle(msg):
    try:
        person_id = msg.get('chat').get('id')
        text = msg.get('text')
        bot.sendChatAction(person_id, "typing")
        log(msg)
        userMsg.insert_one(msg)
        if text.startswith('/'):
            bot.sendMessage(
                person_id, "Please Enter Your Admission Number To See Your Results")
        else:            
            row_result = get_results(text)
            result = format_message(row_result)
            bot.sendMessage(person_id, result)
            botResponse.insert_one({"person_id:": person_id, "result": result});
    except Exception as e:
        bot.sendMessage(
            person_id, "Something went wrong, please try again later")
        errors.insert_one({'error':str(e), "line": 84})
        log("Handle: Error: "+str(e))


def on_inline_query(msg):
    log(msg)
    userMsg.insert_one(msg)
    def compute():
        try:
            query_id, from_id, query_string = telepot.glance(
                msg, flavor='inline_query')
            # print('Inline Query:', query_id, from_id, query_string)
            if len(query_string) >= 6:
                lyrics = format_message(get_results(query_string))
                articles = [InlineQueryResultArticle(
                    id='abc',
                    title="Click Here",
                    input_message_content=InputTextMessageContent(
                        message_text=lyrics
                    )
                )]
                return articles
            else:
                articles = [InlineQueryResultArticle(
                    id='abc',
                    title='Input Admission Number',
                    input_message_content=InputTextMessageContent(
                        message_text="Please Enter Your Admission Number To See Your Results"
                    )
                )]
                return articles
        except Exception as e:
        	errors.insert_one({'error':str(e), "line": 116})
        	log(e)
        	return None
    if compute != None:
        try:
            answerer.answer(msg, compute)
        except Exception as e:
        	errors.insert_one({'error':str(e), "line": 123})
        	log(e)

def on_chosen_inline_result(msg):
    log(msg)
    userMsg.insert_one(msg)
    result_id, from_id, query_string = telepot.glance(
        msg, flavor='chosen_inline_result')
    print('Chosen Inline Result:', result_id, from_id, query_string)


def get_results(admissionId):

    admissionId = admissionId.strip()
    try:
        data = [
          ('admissionNumber', admissionId),
          ('__RequestVerificationToken', 'TtMMZ7TQSi0g-fBtZwJvNJdd6E1ljGLuTud2bKL5Fk2lqI8LGk7CK4tcBqApbLWfFJUEy_IaLj3NZae5uiSDPh4yU16HsUig5dbhKID8Yxk1'),
        ]
        response = requests.post('http://www.app.neaea.gov.et/Student/StudentDetailsx', headers=headers, cookies=cookies, data=data)
        
        if response.status_code == 200:
            if json.loads(response.text):
                student = json.loads(response.text)[0]
                marks_response = requests.post('http://www.app.neaea.gov.et/Student/StudentMark?studentId=' + str(student['Id']) +'&_=1533025370907', headers=headers, cookies=cookies, data=data)
                if marks_response.status_code == 200:
                    subjects = json.loads(marks_response.text)
                    for subject in subjects:
                        key = subject['Subject']
                        student[key] = subject['Result']
                return student
            return None
    except Exception as e:
    	errors.insert_one({'error':str(e), "line": 156})
    	log("GetResults Error: "+str(e))
    	return "Something went wrong, couldn't retrieve results \n"


def format_message(result):

    if result == None:
        return "Not found, Please check if the Admission Id is Valid"

    message = 'Full Name: {} \nSchool: {}\n'.format(result['FullName'], result['School'])
    if result['Stream'] == 'Natural Science':
        keys = ['English', 'Physics', 'Mathematics Nat. Sc.', 'Scholastic Aptitude', 'Chemistry', 'Biology', 'Civics']
    else:
        keys = ['English', 'History', 'Maths, Soc. Sc.', 'Scholastic Aptitude', 'Economics', 'Geography', 'Civics']

    for key in keys:
        message+= emojize(':blue_book:' +""+key+ " "+ str(result[key]) + '\n')

    return message+"\nTotal: {}\n Photo: {}".format(result['TotalMark'], '{}{}'.format(BASE, result['Photo'][1:]).replace(" ", "%20"))


def log(msg):
    with open('log_results.txt', 'a') as logfile:
        now = datetime.datetime.now()
        logfile.write(now.isoformat()+"\t"+str(msg)+"\n\n")


def main():
    MessageLoop(bot, {'chat': handle,
                      'inline_query': on_inline_query,
                      'chosen_inline_result': on_chosen_inline_result}).run_as_thread()

    print('Listening ...')
    log("******************************Server Started at" +
        datetime.datetime.now().isoformat() + "***************************")

    # Keep the program running.
    while 1:
        time.sleep(10)

if __name__ == '__main__':
    main()
