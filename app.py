import flask
from flask import render_template,request,redirect, url_for , jsonify, flash
import requests
import pytz
import pymongo
import copy
import time
from datetime import datetime

api_url = "https://ipl2021-live.herokuapp.com/scorecard?match_no=18"
prediction_mappings= {"prediction_1":"Most Runs","prediction_2":"Most Wickets","prediction_3":"Winning Team","prediction_4":"First Innings Score","prediction_5":"Second Innings Score","points":"points"}
teams = {"bangalore":"rcb","chennai":"csk","kolkata":"kkr","rajasthan":"rr","delhi":"dc","mumbai":"mi","hyderabad":"srh","punjab":"pbks"}
player_mappings = {"mohammad shami":"mohammed shami","amit mishra":"a mishra"}
# MONGODB_URL = 'mongodb+srv://rsumit123:mongoatlas@cluster0.eyg9j.mongodb.net/myFirstDatabase?retryWrites=true&w=majority'
MONGODB_URL = "mongodb://rsumit123:mongoatlas@cluster0-shard-00-00.eyg9j.mongodb.net:27017,cluster0-shard-00-01.eyg9j.mongodb.net:27017,cluster0-shard-00-02.eyg9j.mongodb.net:27017/myFirstDatabase?ssl=true&replicaSet=atlas-dbf0fd-shard-0&authSource=admin&retryWrites=true&w=majority"
app = flask.Flask(__name__)
app.secret_key = "abcd1234abcd123abcd12"
# client = None

def make_connections():
    # global client
    client = pymongo.MongoClient(MONGODB_URL)
    
    # db = client.player_data
    return client

@app.route("/", methods=["GET","POST"])
def home():
    return render_template("index.html")

@app.route("/add_player",methods = ["GET"])
def add_player():
    if request.method == "GET":
        return render_template('add_player.html',data="Enter a unique username")
    


@app.route("/add_player", methods=["POST"])
def add_player_process():
    username = request.form['username'].strip().lower().replace('.','')
    password = request.form['password']
    client = make_connections()
    db = client.player_data
    cc = db["final_player_data"]
    res = list(cc.find())
    exists = False
    
    for user in res:
        if user["username"]==username:
            exists = True
            return render_template('add_player.html',data="Username already exists. Enter a unique username")
    if exists == False:
        
        cc.insert_one({"username":username,"password":password,"points":0})
        cc2 = db["per_match_data"]
        cc2.update_many({},{"$set":{"player_predictions."+username:{"prediction_1":"NA","prediction_2":"NA","prediction_3":"NA","prediction_4":"NA","prediction_5":"NA","points":0}}})
        client.close()

        



    return redirect(url_for('get_leaderboard'))


@app.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    client = make_connections()
    db = client.player_data
    cc = db["final_player_data"]
    res = list(cc.find())
    sorted_d = sorted(res, key=lambda k: k['points'],reverse=True) 
    sorted_di ={}
    for m in sorted_d:
        sorted_di[m['username']] = m['points']
    client.close()


    return render_template('leaderboard.html',result = sorted_di)

def get_data_from_api(match_no):

    data = requests.get(api_url.replace("18",str(match_no))).json()
    return data

@app.route("/predictions", methods=["GET","POST"])
def make_predictions():

    if request.method == "GET":
        tz = pytz.timezone('Asia/Kolkata')
        date_time = datetime.now(tz)

        date_time = date_time.strftime("%Y-%m-%dT%H:%M:%S")
        # date_time = requests.get("http://worldtimeapi.org/api/timezone/Asia/Kolkata").json()["datetime"]
        year,month,day = date_time.split("T")[0].split('-')
        # day="09"
        current_hour,current_min,current_sec = date_time.split("T")[1].split(':')
        current_min = int(current_min.strip())
        current_hour = int(current_hour.strip())

        date = day+"/"+month+"/"+year
        client = make_connections()
        db = client.player_data
        cc2 = db["per_match_data"]
        res = list(cc2.find({"match_date":date},{"_id":0}))
        matches=[]
        for i in res:
            matches.append(str(i["match_no"])+" | "+i["match_name"])
        client.close()

    
        return render_template('prediction.html',activities = matches)
    else:
        # username = request.form["username"].strip().lower()
        # password = request.form["password"]
        tz = pytz.timezone('Asia/Kolkata')
        date_time = datetime.now(tz)

        date_time = date_time.strftime("%Y-%m-%dT%H:%M:%S")
        # date_time = requests.get("http://worldtimeapi.org/api/timezone/Asia/Kolkata").json()["datetime"]
        current_hour,current_min,current_sec = date_time.split("T")[1].split(':')
        current_min = int(current_min.strip())
        current_hour = int(current_hour.strip())
        match_name = request.form["activity"]

        activity = request.form["activity"].split("|")[0].strip()
        client = make_connections()
        db = client.player_data
        
        cc = db["per_match_data"]
        res = cc.find_one({"match_no":int(activity)})
        match_hours = int(res["match_time"].split(":")[0].strip())+12
        match_mins = int(res["match_time"].split(":")[1].replace("PM",'').strip())
        client.close()
        if  (current_hour>match_hours) or (current_hour == match_hours and current_min > 40) :
            flash("Time has passed please select another match")
            return render_template("failure1.html")
        else:
            # print(activity.lower())
            
            playing_teams = []
            for i in teams.keys():
                if i.lower() in match_name.lower():
                    playing_teams.append(teams[i])
                    if len(playing_teams)==2:
                        break

            if len(playing_teams)==2:
                print(playing_teams)
                scoreboard_data = get_data_from_api(int(activity))
                if len(scoreboard_data["playing_eleven"])==2:
                    squad = [scoreboard_data["playing_eleven"][key] for key in scoreboard_data["playing_eleven"].keys()]
                    matches = squad[0]
                    matches.extend(squad[1])
                    # matches = squad.copy()
                else:
                    


                    client = make_connections()

                    cc2 = client["squad_data"]["players"]
                    squad = list(cc2.find({"$or":[{"team":playing_teams[0]},{"team":playing_teams[1]}]},{"_id":0}))
                    matches = [i['player'].lower() for i in squad]
                    
 
                    client.close()
                innings_1_score = ["< 120","121 - 140","141 - 160","161 - 180","181 - 200","200+"]
                innings_2_score = innings_1_score.copy()
                
            else:
                print(playing_teams)
                print("Something is a amiss")
                flash("Unknown Error.. Could not get teams")
                return render_template("failure1.html")
            
            

            
            matches2 = copy.deepcopy(matches)


            return render_template("load_predictions_data.html",activities = matches, activities2=matches2 , match_no = [activity], activities3 = playing_teams , activities4 = innings_1_score , activities5 = innings_2_score)

        # for user in res:
        #     if user['username']==username and user['password']==password:


        # return request.form
@app.route("/submit_predictions",methods=["POST"])
def submit_predictions():
    if request.method=="POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        match_no = int(request.form["no"])
        prediction_1 = request.form["activity"].lower()
        prediction_2 = request.form["activity2"].lower()
        prediction_3 = request.form["activity3"].lower()
        prediction_4 = request.form["activity4"].lower()
        prediction_5 = request.form["activity5"].lower()
        client = make_connections()
        res = client["player_data"]["final_player_data"]
        all_users = list(res.find())
        for user in all_users:
            if user['username']==username and user['password']==password:
                break

        else:
            flash("User not registered. Please register first")
            return render_template("failure1.html")
        # client = make_connections()
        db = client.player_data
        
        cc = db["per_match_data"]
        cc.update_one({"match_no":match_no},{"$set":{"player_predictions."+username+".prediction_1":prediction_1}})
        cc.update_one({"match_no":match_no},{"$set":{"player_predictions."+username+".prediction_2":prediction_2}})
        cc.update_one({"match_no":match_no},{"$set":{"player_predictions."+username+".prediction_3":prediction_3}})
        cc.update_one({"match_no":match_no},{"$set":{"player_predictions."+username+".prediction_4":prediction_4}})
        cc.update_one({"match_no":match_no},{"$set":{"player_predictions."+username+".prediction_5":prediction_5}})
        client.close()


        
        
    
    flash("Predictions successfully saved. Go to Match leaderboard to check your score")   
    return render_template("failure1.html")

@app.route("/match_leaderboard",methods=["GET","POST"])
def match_leaderboard():
    if request.method == "GET":
        client = make_connections()
        db = client.player_data
        
        cc = db["per_match_data"]
        matches = list(cc.find({},{"match_name":1,"_id":0}))
        matches = [i["match_name"] for i in matches]
        client.close()
        return render_template('prediction.html',activities = matches)

        # return render_template('view_predictions.html',matches = matches )

    # if request.method=="GET":
    #     tz = pytz.timezone('Asia/Kolkata')
    #     date_time = datetime.now(tz)

    #     date_time = date_time.strftime("%Y-%m-%dT%H:%M:%S")
    #     # date_time = requests.get("http://worldtimeapi.org/api/timezone/Asia/Kolkata").json()["datetime"]
    #     year,month,day = date_time.split("T")[0].split('-')
    #     # day="25"
    #     current_hour,current_min,current_sec = date_time.split("T")[1].split(':')
    #     current_min = int(current_min.strip())
    #     current_hour = int(current_hour.strip())

    #     date = day+"/"+month+"/"+year
    #     client = make_connections()
    #     db = client.player_data
    #     cc2 = db["per_match_data"]
    #     res = list(cc2.find({"match_date":date},{"_id":0}))
    #     matches=[]
    #     for i in res:
    #         matches.append(str(i["match_no"])+" | "+i["match_name"])
    #     client.close()

    
        
    if request.method == "POST":
        match_name = request.form["activity"]

        # activity = request.form["activity"].split("|")[0].strip()
        client = make_connections()
        db = client.player_data
        
        cc = db["per_match_data"]
        res = cc.find_one({"match_name":match_name})
        # res = cc.find_one({"match_no":int(activity)})
        m = []
        
        for k,v in res["player_predictions"].items():
            mat_lead={}
            mat_lead["username"]=k
            mat_lead['points']=v["points"]
            m.append(mat_lead)

        # res = res["player_predictions"]
        sorted_d = sorted(m, key=lambda k: k['points'],reverse=True) 
        sorted_di ={}
        for m in sorted_d:
            sorted_di[m['username']] = m['points']
        client.close()
        return render_template('match_leaderboard.html',match_no = match_name,result = sorted_di)



    



    


@app.route("/update_final_leaderboard",methods=["GET"])
def update_final_leaderboard():
    client = make_connections()
    db = client.player_data
    cc2 = db["final_player_data"]
    
    res = list(cc2.find())
    users = [i["username"] for i in res]

    cc1 = db["per_match_data"]
    user_points={}
    for user in users:
        p_list = list(cc1.find({},{"player_predictions."+user+".points":1,"_id":0}))
        user_points[user] = sum([i['player_predictions'][user]['points'] for i in p_list])

    for u , p in user_points.items():
        cc2.update_one({"username":u},{"$set":{"points":p}})

    return redirect(url_for('get_leaderboard'))

@app.route("/view_predictions",methods=["GET","POST"])
def view_predictions():
    if request.method == "GET":
        client = make_connections()
        db = client.player_data
        
        cc = db["per_match_data"]
        matches = list(cc.find({},{"match_name":1,"_id":0}))
        matches = [i["match_name"] for i in matches]
        client.close()

        return render_template('view_predictions.html',matches = matches )
    if request.method =="POST":
        # return request.form
        match_name = request.form["match"]
        client = make_connections()
        db = client.player_data
        try:
            cc = db["per_match_data"].find_one({"match_name":match_name})
        except:
            client.close()
            client = make_connections()
            db = client.player_data
            cc = db["per_match_data"].find_one({"match_name":match_name})


        

        return render_template("show_predictions.html",player_predictions = cc['player_predictions'],prediction_mapping = prediction_mappings)

    
@app.route("/update_points/<int:match_no>",methods=["GET"])
def update_points(match_no):
# tz = pytz.timezone('Asia/Kolkata')
# date_time = datetime.now(tz)

# date_time = date_time.strftime("%Y-%m-%dT%H:%M:%S")
# # date_time = requests.get("http://worldtimeapi.org/api/timezone/Asia/Kolkata").json()["datetime"]
# year,month,day = date_time.split("T")[0].split('-')
# day = "25"
# date = day+"/"+month+"/"+year


    client = make_connections()
    db = client.player_data
    cc2 = db["per_match_data"]
    res = cc2.find_one({"match_no":match_no},{"_id":0})
    match_no = res["match_no"]
    user_points = get_points(match_no,res)
    # cc = db["final_player_data"]
    for user,point in user_points.items():
        cc2.update_one({"match_no":match_no},{"$set":{"player_predictions."+user+".points":point}})
        
    
    


    client.close()
    
    return user_points

def get_points(match_no,user_data):
    # match_no=19
    player_points={"prediction_1":{"NA":0,"na":0},"prediction_2":{"NA":0,"na":0},"prediction_3":{"NA":0,"na":0},"prediction_4":{"NA":0,"na":0},"prediction_5":{"NA":0,"na":0}}
    try:

        scorecard_data = requests.get(api_url.replace("18",str(match_no)),verify=False,timeout=10).json()
    except:
        print("Retrying request to api")
        scorecard_data = requests.get(api_url.replace("18",str(match_no)),verify=False,timeout=10).json()

    print(user_data)
    print(user_data["player_predictions"])
    user_points = {}
    for user,pred in user_data["player_predictions"].items():
        print(user,pred)
        print(player_points["prediction_1"])
        print("========================================")
        username = user
        prediction_1 = pred["prediction_1"]

        if prediction_1 not in player_points["prediction_1"]:
            player_points["prediction_1"][prediction_1]=calculate_points_prediction_1(prediction_1,scorecard_data)
        prediction_2 = pred["prediction_2"]
        if prediction_2 not in player_points["prediction_2"]:
            player_points["prediction_2"][prediction_2]=calculate_points_prediction_2(prediction_2,scorecard_data)
        prediction_3 = pred["prediction_3"]
        inv_teams = {v: k for k, v in teams.items()}
        inv_teams["NA"]="na"
        if inv_teams[prediction_3] in scorecard_data["result"]["winning_team"].lower():
            player_points["prediction_3"][prediction_3]=200
        else:
            player_points["prediction_3"][prediction_3]=0
        prediction_4 = pred["prediction_4"]
        if prediction_4 not in player_points["prediction_4"]:
            player_points["prediction_4"][prediction_4] = calculate_points_prediction_4(prediction_4,scorecard_data)
        prediction_5 = pred["prediction_5"]
        if prediction_5 not in player_points["prediction_5"]:
            player_points["prediction_5"][prediction_5] = calculate_points_prediction_5(prediction_5,scorecard_data)

        
        
        user_points[username] = player_points["prediction_1"][prediction_1]+player_points["prediction_2"][prediction_2]+player_points["prediction_3"][prediction_3]+player_points["prediction_4"][prediction_4]+player_points["prediction_5"][prediction_5]
    print("PLAYER POINTS===========================>")
    print(player_points)
    print("User points==============================>")
    print(user_points)

    return user_points



        

def calculate_points_prediction_4(prediction_4,scorecard_data):
    # ["< 120","121 - 140","141 - 160","161 - 180","181 - 200","200+"]
    p_points = 0


    if len(scorecard_data["Innings1"][2]) >1:

        if prediction_4 == "< 120" and scorecard_data["Innings1"][2]["runs"] < 120:
            p_points = 100

        elif prediction_4 == "121 - 140" and 121 <= scorecard_data["Innings1"][2]["runs"] <= 140:
            p_points = 100

        elif prediction_4 == "141 - 160" and 141 <= scorecard_data["Innings1"][2]["runs"] <= 160:
            p_points = 100

        elif prediction_4 == "161 - 180" and 161 <= scorecard_data["Innings1"][2]["runs"] <= 180:
            p_points = 100

        elif prediction_4 == "181 - 200" and 181 <= scorecard_data["Innings1"][2]["runs"] <= 200:
            p_points = 100

        elif prediction_4 == "200+" and scorecard_data["Innings1"][2]["runs"] > 200:
            p_points = 100

        else:
            p_points = 0

    return p_points


def calculate_points_prediction_5(prediction_5,scorecard_data):
    # ["< 120","121 - 140","141 - 160","161 - 180","181 - 200","200+"]
    p_points = 0


    if len(scorecard_data["Innings2"][2]) >1:

        if prediction_5 == "< 120" and scorecard_data["Innings2"][2]["runs"] < 120:
            p_points = 100

        elif prediction_5 == "121 - 140" and 121 <= scorecard_data["Innings2"][2]["runs"] <= 140:
            p_points = 100

        elif prediction_5 == "141 - 160" and 141 <= scorecard_data["Innings2"][2]["runs"] <= 160:
            p_points = 100

        elif prediction_5 == "161 - 180" and 161 <= scorecard_data["Innings2"][2]["runs"] <= 180:
            p_points = 100

        elif prediction_5 == "181 - 200" and 181 <= scorecard_data["Innings2"][2]["runs"] <= 200:
            p_points = 100

        elif prediction_5 == "200+" and scorecard_data["Innings2"][2]["runs"] > 200:
            p_points = 100

        else:
            p_points = 0

    return p_points


        

        

            


        
    

                
def calculate_points_prediction_2(prediction_2,scorecard_data):
    p_points=0
    for player_data in scorecard_data["Innings1"][1]["Bowlers"]:
        
        if prediction_2.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_2.lower() :
            
            p_points=calculate_points_for_wickets(player_data,scorecard_data)
            # player_points[prediction_1] = p_points
            return p_points
        
        # elif prediction_2.lower().split()[1] in player_data["name"].split()[1].lower():
        #     p_points=calculate_points_for_wickets(player_data,scorecard_data)
        #     # player_points[prediction_1] = p_points
        #     return p_points
        
        
        
        # elif prediction_2.lower().split()[1] in player_data["name"]:
        #     p_points=calculate_points_for_wickets(player_data,scorecard_data)
        #     # player_points[prediction_1] = p_points
        #     return p_points

    for player_data in scorecard_data["Innings2"][1]["Bowlers"]:
        
        if prediction_2.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_2.lower() :
            
            p_points=calculate_points_for_wickets(player_data,scorecard_data)
            # player_points[prediction_1] = p_points
            return p_points

    ###################CHECKING MAPPINGS===================================================


    if prediction_2 in player_mappings:

        prediction_2 = player_mappings[prediction_2]

        for player_data in scorecard_data["Innings1"][1]["Bowlers"]:
        
            if prediction_2.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_2.lower() :
                
                p_points=calculate_points_for_wickets(player_data,scorecard_data)
                # player_points[prediction_1] = p_points
                return p_points
        for player_data in scorecard_data["Innings2"][1]["Bowlers"]:
        
            if prediction_2.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_2.lower() :
                
                p_points=calculate_points_for_wickets(player_data,scorecard_data)
                # player_points[prediction_1] = p_points
                return p_points
        



    
        
        # elif prediction_2.lower().split()[1] in player_data["name"].split()[1].lower():
        #     p_points=calculate_points_for_wickets(player_data,scorecard_data)
        #     # player_points[prediction_1] = p_points
        #     return p_points
        
        
        
        # elif prediction_2.lower().split()[1] in player_data["name"]:
        #     p_points=calculate_points_for_wickets(player_data,scorecard_data)
        #     # player_points[prediction_1] = p_points
        #     return p_points

    return p_points

def calculate_points_for_wickets(player_data,scorecard_data):
    p_wickets_taken = int(player_data["wicket"])
    if p_wickets_taken == 0:
        return 0
    wickets = []
    for pl in scorecard_data["Innings1"][1]["Bowlers"]:
        wickets.append(int(pl["wicket"]))
    for pl in scorecard_data["Innings2"][1]["Bowlers"]:
        wickets.append(int(pl["wicket"]))
    h_wickets_taken = max(wickets)
    p_points = int((p_wickets_taken/h_wickets_taken)*100)
    return p_points



                
                
                

def calculate_points_prediction_1(prediction_1,scorecard_data):
    # player_points = {}
    p_points = 0
    
    for player_data in scorecard_data["Innings1"][0]["Batsman"]:
        
        if prediction_1.lower().strip() in player_data["name"].lower().replace('(c)','').replace('(wk)','').strip() or player_data["name"].lower().replace('(c)','').replace('(wk)','').strip() in prediction_1.lower() :
            
            p_points=calculate_points_for_runs(player_data,scorecard_data)
            # player_points[prediction_1] = p_points
            return p_points
        
        # elif prediction_1.lower().split()[1] in player_data["name"].split()[1].lower():
        #     p_points=calculate_points_for_runs(player_data,scorecard_data)
        #     # player_points[prediction_1] = p_points
        #     break
        
        
        
        # elif prediction_1.lower().split()[1] in player_data["name"]:
        #     p_points=calculate_points_for_runs(player_data,scorecard_data)
        #     # player_points[prediction_1] = p_points
        #     break
    for player_data in scorecard_data["Innings2"][0]["Batsman"]:
        
        if prediction_1.lower().strip() in player_data["name"].lower().replace('(c)','').replace('(wk)','').strip() or player_data["name"].lower().replace('(c)','').replace('(wk)','').strip() in prediction_1.lower() :
            
            p_points=calculate_points_for_runs(player_data,scorecard_data)
            # player_points[prediction_1] = p_points
            return p_points


    #####################################################CALCULATE MAPPINGS===========






    if prediction_1 in player_mappings:

        prediction_1 = player_mappings[prediction_1]

        for player_data in scorecard_data["Innings1"][0]["Batsman"]:
        
            if prediction_1.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_1.lower() :
                
                p_points=calculate_points_for_wickets(player_data,scorecard_data)
                # player_points[prediction_1] = p_points
                return p_points
        for player_data in scorecard_data["Innings2"][0]["Batsman"]:
        
            if prediction_1.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_1.lower() :
                
                p_points=calculate_points_for_wickets(player_data,scorecard_data)
                # player_points[prediction_1] = p_points
                return p_points

    return p_points





def calculate_points_for_runs(player_data,scorecard_data):
    
    p_runs_scored = int(player_data["runs"])
    runs = []
    for pl in scorecard_data["Innings1"][0]["Batsman"]:
        runs.append(int(pl["runs"]))
    for pl in scorecard_data["Innings2"][0]["Batsman"]:
        runs.append(int(pl["runs"]))
    h_runs_scored = max(runs)
    p_points = int((p_runs_scored/h_runs_scored)*100)
    print(player_data['name']+" : "+str(p_points))
    return p_points
    









@app.route("/delete_user",methods=["GET","POST"])
def delete_user():
    if request.method == "GET":
        return render_template("delete_user.html")
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        client = make_connections()
        res = client["player_data"]["final_player_data"]
        all_users = list(res.find())
        for user in all_users:
            if user['username']==username and user['password']==password:
                break
        else:
            flash("User not found or user/password incorrect")
            return render_template("failure1.html")
        res1 = client["player_data"]["per_match_data"]
        res1.update_many({},{"$unset":{"player_predictions."+username:1}})
        res.delete_one({"username":username})
        flash(username+" Deleted")
        return render_template("failure1.html")



    


        




        







if __name__ == "__main__":
	print("* Loading..."+"please wait until server has fully started")

	make_connections()


	app.run(host='0.0.0.0', port=5000,debug=True)

