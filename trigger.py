import pytz
import requests
from datetime import datetime
from app import update_points
import pymongo
import time

MONGODB_URL = "mongodb://rsumit123:mongoatlas@cluster0-shard-00-00.eyg9j.mongodb.net:27017,cluster0-shard-00-01.eyg9j.mongodb.net:27017,cluster0-shard-00-02.eyg9j.mongodb.net:27017/myFirstDatabase?ssl=true&replicaSet=atlas-dbf0fd-shard-0&authSource=admin&retryWrites=true&w=majority"
api_url = "https://ipl2021-live.herokuapp.com/scorecard?match_no=18"

def make_connections():
    # global client
    client = pymongo.MongoClient(MONGODB_URL)
    
    # db = client.player_data
    return client



def trigger_update():
    tz = pytz.timezone('Asia/Kolkata')
    date_time = datetime.now(tz)

    date_time = date_time.strftime("%Y-%m-%dT%H:%M:%S")
    # date_time = requests.get("http://worldtimeapi.org/api/timezone/Asia/Kolkata").json()["datetime"]
    year,month,day = date_time.split("T")[0].split('-')
    # day = "25"
    date = day+"/"+month+"/"+year
    client = make_connections()
    db = client.player_data
    cc2 = db["per_match_data"]
    res = list(cc2.find({"match_date":date},{"_id":0}))
    client.close()
    p3 = {i['match_no'] : False for i in res}
    
    while(True):
        

        for match in res:
            
            match_no = match["match_no"]
            # match_no=21
            print("Checking for match no: ",match_no)
            scorecard_data = requests.get(api_url.replace("18",str(match_no)),verify=False,timeout=10).json()
            # if True:
            if "the scorecard will" not in scorecard_data["result"]["update"] and scorecard_data["result"]["winning_margin"].lower()=="na":
                p3[match_no] = True
                update_points(match_no)
            else:
                if p3[match_no]==True:
                    update_points(match_no)
                

                    p3[match_no] = False
                print("match has not started yet or is completed")
        print("points updated .. sleeping for 600 seconds")
        time.sleep(600)



trigger_update()