from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, RegexHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters)

import logging
import sqlite3
import datetime
import time
import threading
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                    level=logging.INFO)

ROOMNAME, CATEGORY, SHOWTIME = range(3)

categoryDict={}

def initDB():
    try:
        conn=sqlite3.connect("watch2gether.db")
        cursor=conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS TB_ROOM
            (PK_ROOMID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            DATE_CREATED DATETIME NOT NULL,
            URL TEXT NOT NULL,
            CODE_CATEGORY NOT NULL,
            CREATER TEXT NOT NULL)
            ''')
                
        cursor.execute('''CREATE TABLE IF NOT EXISTS TB_CODE_CATEGORY
            (CODE PRIMARY KEY NOT NULL,
            DESCRIPTION TEXT NOT NULL)
            ''')

        cursor.execute('''INSERT INTO TB_CODE_CATEGORY(CODE,DESCRIPTION)
            SELECT 'CAT0001','Drama' WHERE NOT EXISTS(SELECT 1 FROM TB_CODE_CATEGORY WHERE CODE='CAT0001')
            ''')

        cursor.execute('''INSERT INTO TB_CODE_CATEGORY(CODE,DESCRIPTION)
            SELECT 'CAT0002','Horror' WHERE NOT EXISTS(SELECT 1 FROM TB_CODE_CATEGORY WHERE CODE='CAT0002')
            ''')

        cursor.execute('''INSERT INTO TB_CODE_CATEGORY(CODE,DESCRIPTION)
            SELECT 'CAT0003','Romantic' WHERE NOT EXISTS(SELECT 1 FROM TB_CODE_CATEGORY WHERE CODE='CAT0003')
            ''')

        conn.commit()
    except Exception as e:
        print(e)
    finally:
        conn.close()

def getCategoryDict():
    global categoryDict
    try:
        conn=sqlite3.connect('watch2gether.db')
        cursor=conn.cursor()
        resultSet=cursor.execute(
            '''
            SELECT CODE,DESCRIPTION FROM TB_CODE_CATEGORY
            '''
        )

        for row in resultSet:
            categoryDict[row[0]]=row[1]
    except Exception as e:
        print(e)
    finally:
        conn.close()

def start(bot,update):
    update.message.reply_text(
        'Hi! I am Watch2gether Bot, pleasure to serve you.\n'
        '<a>/createroom</a> - Create a room and set showtime\n'
        '<a>/viewroom</a>   - View available room\n',
        parse_mode='html',
        reply_markup=ReplyKeyboardRemove()
    )

def create_room(bot,update):
    global intputRoomName
    global inputCategory
    global inputShowTime
    inputRoomName=''
    inputCategory=''
    inputShowTime=''
    
    update.message.reply_text(
        'Please tell me your room name?'
    )

    return ROOMNAME

def room_name(bot,update):
    global inputRoomName
    global categoryDict
    
    inputRoomName=update.message.text
    
    #reply_keyboard=[]
    keyboard = []
    
    for i in categoryDict.keys():
        #reply_keyboard.append([InlineKeyboardButton(categoryDict[i],callback_data=i)])
        keyboard.append([InlineKeyboardButton(categoryDict[i],callback_data=i)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        'I see! Let\'s call your room [<b>'+inputRoomName+'</b>]\n'
        'Now choose one of the category from below',
        parse_mode='html',
        #reply_markup=InlineKeyboardMarkup(reply_keyboard)
        reply_markup = reply_markup
    )
    return CATEGORY

def category(bot,update):
    global categoryDict
    global inputCategory
    schedule = [1,2,3,4]
    keyboard = [
        [InlineKeyboardButton(u"Now", callback_data=str(schedule[0]))],
        [InlineKeyboardButton(u"Within 1 hour", callback_data=str(schedule[1]))],
        [InlineKeyboardButton(u"Within 12 hours", callback_data=str(schedule[2]))],
        [InlineKeyboardButton(u"Next day", callback_data=str(schedule[3]))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query=update.callback_query
    inputcategory=query.data
    
    bot.edit_message_text(text="You have selected: {}".format(inputcategory) + "\n Please enter showtime",
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id)
     
    bot.edit_message_reply_markup(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        reply_markup=reply_markup
    )
    
    return SHOWTIME

def showtime(bot,update):
    query=update.callback_query
    bot.send_message(chat_id = query.message.chat_id, 
                            text = "I'm opening room for you, please hang on.")
    chrome_options = Options() 
    chrome_options.add_argument("--headless")
    if os.name == "nt":
            driver = webdriver.Chrome(executable_path="chromedriver.exe", chrome_options = chrome_options)
    elif os.name == "posix":
            driver = webdriver.Chrome("./chromedriver" , chrome_options = chrome_options)
    driver.wait = WebDriverWait(driver, 5)

    driver.get('https://www.watch2gether.com') #going to site
    driver.find_element_by_css_selector('.ui.primary.button').click()
    room_url = driver.current_url
    driver.quit()

    keyboard = [[InlineKeyboardButton("Room Url", room_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id = query.message.chat_id, text = 'Your room is ready', reply_markup = reply_markup)

    create_time = update.message.date
    creater = update.message.chat['first_name'] + update.message.chat['last_name']

    data_store(create_time, room_url, creater)

def view_room(bot,update):
    global categoryDict
    
    inputRoomName=update.message.text
    
    reply_keyboard=[]
    for i in categoryDict.keys():
        reply_keyboard.append([InlineKeyboardButton(categoryDict[i],callback_data=i)])
        
    update.message.reply_text(
        'Please select your favourite category',
        parse_mode='html',
        reply_markup=InlineKeyboardMarkup(reply_keyboard)
    )
    return CATEGORY

def cancel(bot,udpate):
    return

def main():
    initDB()
    getCategoryDict()
    
    updater = Updater(token = '441243370:AAFADtpDKCcfVxdlmvnuY36fVhDQPeU3cJM')
    
    create_conversation=ConversationHandler(
        entry_points=[CommandHandler('createroom',create_room)],

        states={
            ROOMNAME:[MessageHandler(Filters.text,room_name)],
            CATEGORY:[CallbackQueryHandler(category)],
            #SHOWTIME:[RegexHandler('^((Today)|(Tommorow)) ([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$',showtime)]
            SHOWTIME:[CallbackQueryHandler(showtime)]
        },

        fallbacks=[CommandHandler('cancel',cancel)]
    )

    view_conversation=ConversationHandler(
        entry_points=[CommandHandler('viewroom',view_room)],

        states={
            CATEGORY:[CallbackQueryHandler(category)]
        },

        fallbacks=[CommandHandler('cancel',cancel)]
    )
    
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(create_conversation)
    dispatcher.add_handler(view_conversation)

    updater.start_polling()
    

if __name__=='__main__':
    main()
