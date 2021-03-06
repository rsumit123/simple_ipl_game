import flask
from flask import render_template, request, redirect, url_for, jsonify, flash
import requests
import pytz
import pymongo
import copy
import time
from datetime import datetime
import os
dropdown_players = None
no_of_predictions = 7


api_url = "https://cricket-scorecard-2021.herokuapp.com/scorecard?ipl_match_no=18"




prediction_mappings = {"prediction_1": "Most Runs", "prediction_2": "Most Wickets", "prediction_3": "Winning Team", "prediction_4": "First Innings Score",
                       "prediction_5": "Second Innings Score", "prediction_6": "Most Sixes", "prediction_7": "Mode of Dismissals", "points": "points"}
teams = {"bangalore": "rcb", "chennai": "csk", "kolkata": "kkr", "rajasthan": "rr",
         "delhi": "dc", "mumbai": "mi", "hyderabad": "srh", "punjab": "pbks"}
player_mappings = {"mohammad shami": "mohammed shami",
                   "amit mishra": "a mishra"}

MONGODB_URL = os.environ['MONGODB_URL']
APP_SECRET_KEY = os.environ['APP_SECRET_KEY']

app = flask.Flask(__name__)
app.secret_key = APP_SECRET_KEY


def make_connections():
    ''' return mongodb connections '''
    client = pymongo.MongoClient(MONGODB_URL)

    return client


@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("index.html")


@app.route("/add_player", methods=["GET"])
def add_player():
    ''' Register a new player '''
    if request.method == "GET":
        return render_template('add_player.html', data="Enter a unique username")


@app.route("/add_player", methods=["POST"])
def add_player_process():
    ''' Register a new player '''

    username = request.form['username'].strip().lower().replace('.', '')
    password = request.form['password']
    client = make_connections()
    db = client.player_data
    cc = db["final_player_data"]
    res = list(cc.find())
    exists = False

    for user in res:
        if user["username"] == username:
            exists = True
            return render_template('add_player.html', data="Username already exists. Enter a unique username")
    if exists == False:

        cc.insert_one(
            {"username": username, "password": password, "points": 0})
        cc2 = db["per_match_data"]
        cc2.update_many({}, {"$set": {"player_predictions."+username: {"prediction_1": "NA", "prediction_2": "NA", "prediction_3": "NA",
                                                                       "prediction_4": "NA", "prediction_5": "NA", "prediction_6": "NA", "points": 0, "prediction_7": "NA"}}})
        client.close()

    return redirect(url_for('get_leaderboard'))


@app.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    ''' Get user points based on their predictions '''


    client = make_connections()
    db = client.player_data
    cc = db["final_player_data"]
    res = list(cc.find())
    sorted_d = sorted(res, key=lambda k: k['points'], reverse=True)
    sorted_di = {}
    for m in sorted_d:
        sorted_di[m['username']] = m['points']
    client.close()

    return render_template('leaderboard.html', result=sorted_di)


def get_data_from_api(match_no):

    data = requests.get(api_url.replace("18", str(match_no))).json()
    return data


def get_dropdown_values(selected_class, selected_class_1, selected_class_2):

    pla = []
    if selected_class_1 is not None:
        selected_class_1_l = selected_class_1.lower()
    else:
        selected_class_1_l = ""

    if selected_class_2 is not None:
        selected_class_2_l = selected_class_2.lower()
    else:
        selected_class_2_l = ""

    for i in dropdown_players:
        if i == "-- Select Batsman --" or i.lower() != selected_class.lower() and i.lower() != selected_class_1_l and i.lower() != selected_class_2_l:
            pla.append(i)

    # class_entry_relations = {'class1': ['val1', 'val2'],
            #  'class2': ['foo', 'bar', 'xyz']}

    return pla


@app.route('/_update_dropdown')
def update_dropdown():

    # the value of the first dropdown (selected by the user)
    selected_class = request.args.get('selected_class', type=str)
    selected_class1 = request.args.get('selected_class_1', type=str)
    selected_class2 = request.args.get('selected_class_2', type=str)
    print("class", selected_class)
    print("class1", selected_class1)

    # get values for the second dropdown
    updated_values = get_dropdown_values(
        selected_class, selected_class1, selected_class2)

    # create the value sin the dropdown as a html string
    html_string_selected = ''
    for entry in updated_values:
        html_string_selected += '<option value="{}">{}</option>'.format(
            entry, entry)

    return jsonify(html_string_selected=html_string_selected)


@app.route("/predictions", methods=["GET", "POST"])
def make_predictions():

    if request.method == "GET":
        tz = pytz.timezone('Asia/Kolkata')
        date_time = datetime.now(tz)

        date_time = date_time.strftime("%Y-%m-%dT%H:%M:%S")
        # date_time = requests.get("http://worldtimeapi.org/api/timezone/Asia/Kolkata").json()["datetime"]
        year, month, day = date_time.split("T")[0].split('-')
        # day="09"
        # month = "04"
        current_hour, current_min, current_sec = date_time.split("T")[
            1].split(':')
        current_min = int(current_min.strip())
        current_hour = int(current_hour.strip())

        date = day+"/"+month+"/"+year
        client = make_connections()
        db = client.player_data
        cc2 = db["per_match_data"]
        res = list(cc2.find( {},{"_id": 0}))#{"match_date": date},
        
        matches = []
        for i in res:
            matches.append(str(i["match_no"])+" | "+i["match_name"])

        matches = sorted(matches, key=lambda k: int(k.split('|')[0].strip()))
        
        client.close()

        return render_template('prediction.html', activities=matches)
    else:
        
        tz = pytz.timezone('Asia/Kolkata')
        date_time = datetime.now(tz)

        date_time = date_time.strftime("%Y-%m-%dT%H:%M:%S")
        current_hour, current_min, current_sec = date_time.split("T")[
            1].split(':')
        current_min = int(current_min.strip())
        current_hour = int(current_hour.strip())
        match_name = request.form["activity"]

        activity = request.form["activity"].split("|")[0].strip()
        client = make_connections()
        db = client.player_data

        cc = db["per_match_data"]
        res = cc.find_one({"match_no": int(activity)})
        match_hours = int(res["match_time"].split(":")[0].strip())+12
        match_mins = int(res["match_time"].split(":")[
                         1].replace("PM", '').strip())
        client.close()
        if 1==2:
        # if (current_hour > match_hours) or (current_hour == match_hours and current_min > 40):
            flash("Time has passed please select another match")
            return render_template("failure1.html")
        else:
            # print(activity.lower())

            playing_teams = []
            for i in teams.keys():
                if i.lower() in match_name.lower():
                    playing_teams.append(teams[i])
                    if len(playing_teams) == 2:
                        break

            if len(playing_teams) == 2:
                print(playing_teams)
                scoreboard_data = get_data_from_api(int(activity))
                if len(scoreboard_data["playing_eleven"]) == 2:
                    squad = [scoreboard_data["playing_eleven"][key]
                             for key in scoreboard_data["playing_eleven"].keys()]
                    matches = squad[0]
                    matches.extend(squad[1])
                    # matches = squad.copy()
                else:

                    client = make_connections()

                    cc2 = client["squad_data"]["players"]
                    squad = list(cc2.find(
                        {"$or": [{"team": playing_teams[0]}, {"team": playing_teams[1]}]}, {"_id": 0}))
                    matches = [i['player'].lower() for i in squad]

                    client.close()
                innings_1_score = ["< 120", "121 - 140",
                                   "141 - 160", "161 - 180", "181 - 200", "200+"]
                innings_2_score = innings_1_score.copy()
                mode_of_dismissals = [
                    "caught", "lbw", "bold", "stump", "runout"]

            else:
                print(playing_teams)
                print("Something is a amiss")
                flash("Unknown Error.. Could not get teams")
                return render_template("failure1.html")

            matches2 = copy.deepcopy(matches)
            matches3 = copy.deepcopy(matches)
            matches3.insert(0, "-- Select Batsman --")
            global dropdown_players
            dropdown_players = copy.deepcopy(matches3)

            return render_template("load_predictions_data.html", activities0=matches, activities1=matches2, match_no=[activity], activities2=playing_teams, activities3=innings_1_score, activities4=innings_2_score, activities5=playing_teams, activities6=matches3, activities6_1=mode_of_dismissals)

        # for user in res:
        #     if user['username']==username and user['password']==password:

        # return request.form


@app.route("/submit_predictions", methods=["POST"])
def submit_predictions():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        match_no = int(request.form["no"])
        grouped_predictions = {}
        predictions = [None]*no_of_predictions
        for i in range(0, no_of_predictions-1):
            predictions[i] = request.form["activity"+str(i)].lower()
        for i in range(0, 4):
            grouped_predictions[request.form["activity" +
                                             str(i+6)].lower()] = request.form["activity"+str(i+6)+"_1"].lower()

        predictions[no_of_predictions-1] = grouped_predictions
        
        client = make_connections()
        res = client["player_data"]["final_player_data"]
        all_users = list(res.find())
        for user in all_users:
            if user['username'] == username and user['password'] == password:
                break

        else:
            flash("User not registered. Please register first")
            return render_template("failure1.html")
        # client = make_connections()
        db = client.player_data

        cc = db["per_match_data"]
        for i in range(0, no_of_predictions):
            cc.update_one({"match_no": match_no}, {"$set": {
                          "player_predictions."+username+".prediction_"+str(i+1): predictions[i]}})
            

        client.close()

    flash("Predictions successfully saved. Go to Match leaderboard to check your score")
    return render_template("failure1.html")


@app.route("/match_leaderboard", methods=["GET", "POST"])
def match_leaderboard():
    if request.method == "GET":
        client = make_connections()
        db = client.player_data

        cc = db["per_match_data"]
        matches = list(cc.find({}, {"match_name": 1, "match_no": 1, "_id": 0}))
        matches = sorted(matches, key=lambda k: k['match_no'])
        matches = [i["match_name"] for i in matches]
        client.close()
        return render_template('prediction.html', activities=matches)

        

    if request.method == "POST":
        match_name = request.form["activity"]

        # activity = request.form["activity"].split("|")[0].strip()
        client = make_connections()
        db = client.player_data

        cc = db["per_match_data"]
        res = cc.find_one({"match_name": match_name})
        # res = cc.find_one({"match_no":int(activity)})
        m = []

        for k, v in res["player_predictions"].items():
            mat_lead = {}
            mat_lead["username"] = k
            mat_lead['points'] = v["points"]
            m.append(mat_lead)

        # res = res["player_predictions"]
        sorted_d = sorted(m, key=lambda k: k['points'], reverse=True)
        sorted_di = {}
        for m in sorted_d:
            sorted_di[m['username']] = m['points']
        client.close()
        return render_template('match_leaderboard.html', match_no=match_name, result=sorted_di)


@app.route("/update_final_leaderboard", methods=["GET"])
def update_final_leaderboard():
    client = make_connections()
    db = client.player_data
    cc2 = db["final_player_data"]

    res = list(cc2.find())
    users = [i["username"] for i in res]

    cc1 = db["per_match_data"]
    user_points = {}
    for user in users:
        p_list = list(
            cc1.find({}, {"player_predictions."+user+".points": 1, "_id": 0}))
        user_points[user] = sum(
            [i['player_predictions'][user]['points'] for i in p_list])

    for u, p in user_points.items():
        cc2.update_one({"username": u}, {"$set": {"points": p}})

    return redirect(url_for('get_leaderboard'))


@app.route("/view_predictions", methods=["GET", "POST"])
def view_predictions():

    if request.method == "GET":
        client = make_connections()
        db = client.player_data

        cc = db["per_match_data"]
        matches = list(cc.find({}, {"match_name": 1, "match_no": 1, "_id": 0}))
        matches = sorted(matches, key=lambda k: k['match_no'])
        matches = [i["match_name"] for i in matches]
        client.close()

        return render_template('view_predictions.html', matches=matches)
    if request.method == "POST":
        # return request.form
        match_name = request.form["match"]
        client = make_connections()
        db = client.player_data
        try:
            cc = db["per_match_data"].find_one({"match_name": match_name})
            client.close()
        except:
            client.close()
            client = make_connections()
            db = client.player_data
            cc = db["per_match_data"].find_one({"match_name": match_name})
            client.close()

        return render_template("show_predictions.html", player_predictions=cc['player_predictions'], match_name=match_name, prediction_mapping=prediction_mappings)


@app.route("/points_breakdown", methods=["GET", "POST"])
def points_breakdown():
    # if request.method == "GET":
    #     client = make_connections()
    #     db = client.player_data

    #     cc = db["per_match_data"]
    #     matches = list(cc.find({},{"match_name":1,"match_no":1,"_id":0}))
    #     matches = sorted(matches, key=lambda k: k['match_no'])
    #     matches = [i["match_name"] for i in matches]
    #     client.close()

    #     return render_template('view_predictions.html',matches = matches )

    if request.method == "GET":
        # return request.form
        match_name = request.args.get("match_name")
        # match_name = request.form["match"]
        client = make_connections()
        db = client.player_data
        try:
            cc = db["per_match_data"].find_one({"match_name": match_name})
            match_no = cc['match_no']
            player_preds = cc["player_predictions"]
            client.close()
        except:
            client.close()
            client = make_connections()
            db = client.player_data
            cc = db["per_match_data"].find_one({"match_name": match_name})
            match_no = cc['match_no']
            player_preds = cc["player_predictions"]
            client.close()
        r_dict = update_points(match_no)
        player_points = r_dict["player_points"]
        user_points = r_dict["user_points"]
        grouped_predictions = r_dict["group_points"]

        p_b = {}
        for player, preds in player_preds.items():
            p_b[player] = {}
            p_b[player]["Most Runs"] = {
                preds["prediction_1"]: player_points["prediction_1"][preds["prediction_1"]]}
            p_b[player]["Most Wickets"] = {
                preds["prediction_2"]: player_points["prediction_2"][preds["prediction_2"]]}
            p_b[player]["Winning Team"] = {
                preds["prediction_3"]: player_points["prediction_3"][preds["prediction_3"]]}
            p_b[player]["Innings 1 Score"] = {
                preds["prediction_4"]: player_points["prediction_4"][preds["prediction_4"]]}
            p_b[player]["Innings 2 Score"] = {
                preds["prediction_5"]: player_points["prediction_5"][preds["prediction_5"]]}
            p_b[player]["Most Sixes"] = {
                preds["prediction_6"]: player_points["prediction_6"][preds["prediction_6"]]}
            if type(preds["prediction_7"]) is str:
                itr = {}
            else:

                itr = preds["prediction_7"]
            p_b[player]["Mode of Dismissal_1"] = {"NA": 0}
            p_b[player]["Mode of Dismissal_2"] = {"NA": 0}
            p_b[player]["Mode of Dismissal_3"] = {"NA": 0}
            p_b[player]["Mode of Dismissal_4"] = {"NA": 0}
            i = 0
            for k, v in itr.items():
                p_b[player]["Mode of Dismissal_" +
                            str(i+1)] = {k+"|"+v: grouped_predictions[k+"|"+v]}
                i += 1
            p_b[player]["Total Points"] = {"points_total": user_points[player]}

        print(p_b)

        return render_template("view_breakdown.html", player_prediction_data=p_b, match_name=match_name)


@app.route("/update_points/<int:match_no>", methods=["GET"])
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
    res = cc2.find_one({"match_no": match_no}, {"_id": 0})
    match_no = res["match_no"]
    user_points, player_points, group_points = get_points(match_no, res)
    # cc = db["final_player_data"]
    for user, point in user_points.items():
        cc2.update_one({"match_no": match_no}, {
                       "$set": {"player_predictions."+user+".points": point}})

    client.close()
    r_dict = {"user_points": user_points,
              "player_points": player_points, "group_points": group_points}

    return r_dict


def get_points(match_no, user_data):
    # match_no=19
    player_points = {"prediction_1": {"NA": 0, "na": 0}, "prediction_2": {"NA": 0, "na": 0}, "prediction_3": {
        "NA": 0, "na": 0}, "prediction_4": {"NA": 0, "na": 0}, "prediction_5": {"NA": 0, "na": 0}, "prediction_6": {"NA": 0, "na": 0}}
    group_points = {"-- Select Batsman --|bold": 0}
    try:

        scorecard_data = requests.get(api_url.replace(
            "18", str(match_no)), verify=False, timeout=10).json()
    except:
        print("Retrying request to api")
        scorecard_data = requests.get(api_url.replace(
            "18", str(match_no)), verify=False, timeout=10).json()

    print(user_data)
    print(user_data["player_predictions"])
    user_points = {}
    for user, pred in user_data["player_predictions"].items():
        print(user, pred)
        print(player_points["prediction_1"])
        print("========================================")
        username = user
        prediction_1 = pred["prediction_1"]

        if prediction_1 not in player_points["prediction_1"]:
            player_points["prediction_1"][prediction_1] = calculate_points_prediction_1(
                prediction_1, scorecard_data)
        prediction_2 = pred["prediction_2"]
        if prediction_2 not in player_points["prediction_2"]:
            player_points["prediction_2"][prediction_2] = calculate_points_prediction_2(
                prediction_2, scorecard_data)
        prediction_3 = pred["prediction_3"]
        inv_teams = {v: k for k, v in teams.items()}
        inv_teams["NA"] = "na"
        if inv_teams[prediction_3] in scorecard_data["result"]["winning_team"].lower():
            player_points["prediction_3"][prediction_3] = 200
        else:
            player_points["prediction_3"][prediction_3] = 0
        prediction_4 = pred["prediction_4"]
        if prediction_4 not in player_points["prediction_4"]:
            player_points["prediction_4"][prediction_4] = calculate_points_prediction_4(
                prediction_4, scorecard_data)
        prediction_5 = pred["prediction_5"]
        if prediction_5 not in player_points["prediction_5"]:
            player_points["prediction_5"][prediction_5] = calculate_points_prediction_5(
                prediction_5, scorecard_data)
        prediction_6 = pred["prediction_6"]
        if prediction_6 not in player_points["prediction_6"]:
            player_points["prediction_6"][prediction_6] = calculate_points_prediction_6(
                prediction_6, scorecard_data)

        prediction_7 = pred["prediction_7"]
        if type(prediction_7) is dict:
            for batter, m_dismissal in prediction_7.items():
                if batter+"|"+m_dismissal not in group_points:
                    group_points[batter+"|"+m_dismissal] = calculate_points_prediction_7(
                        batter, m_dismissal, scorecard_data)

        user_points[username] = player_points["prediction_1"][prediction_1]+player_points["prediction_2"][prediction_2]+player_points["prediction_3"][prediction_3] + \
            player_points["prediction_4"][prediction_4] + \
            player_points["prediction_5"][prediction_5] + \
            player_points["prediction_6"][prediction_6]
        if type(prediction_7) is dict:
            for batter, m_dismissal in prediction_7.items():
                user_points[username] += group_points[batter+"|"+m_dismissal]
    print("PLAYER POINTS===========================>")
    print(player_points)
    print("User points==============================>")
    print(user_points)
    print("Group points==============================>")
    print(group_points)

    return user_points, player_points, group_points


def calculate_points_prediction_7(batter, m_dismissal, scorecard_data):
    p_points = 0

    for player_data in scorecard_data["Innings1"][0]["Batsman"]:

        if batter.lower().replace('(c)', '').replace('(wk)', '').strip() in player_data["name"].lower().replace('(c)', '').replace('(wk)', '').strip() or player_data["name"].lower().replace('(c)', '').replace('(wk)', '').strip() in batter.lower().replace('(c)', '').replace('(wk)', '').strip():

            p_points = calculate_points_for_dismissal(
                player_data, m_dismissal, scorecard_data)
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

        if batter.lower().replace('(c)', '').replace('(wk)', '').strip() in player_data["name"].lower().replace('(c)', '').replace('(wk)', '').strip() or player_data["name"].lower().replace('(c)', '').replace('(wk)', '').strip() in batter.replace('(c)', '').replace('(wk)', '').strip().lower():

            p_points = calculate_points_for_dismissal(
                player_data, m_dismissal, scorecard_data)
            # player_points[prediction_1] = p_points
            return p_points

    # CALCULATE MAPPINGS===========

    if batter in player_mappings:

        batter = player_mappings[batter]

        for player_data in scorecard_data["Innings1"][0]["Batsman"]:

            if batter.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in batter.lower():

                p_points = calculate_points_for_dismissal(
                    player_data, m_dismissal, scorecard_data)
                # player_points[prediction_1] = p_points
                return p_points
        for player_data in scorecard_data["Innings2"][0]["Batsman"]:

            if batter.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in batter.lower():

                p_points = calculate_points_for_dismissal(
                    player_data, m_dismissal, scorecard_data)
                # player_points[prediction_1] = p_points
                return p_points

    return p_points


def calculate_points_for_dismissal(player_data, m_dismissal, scorecard_data):

    p_points = 0

    if m_dismissal == "caught" and player_data["dismissal"].startswith("c "):
        p_points = 25

    elif m_dismissal == "bold" and player_data["dismissal"].startswith("b "):
        p_points = 50

    elif m_dismissal == "stump" and player_data["dismissal"].startswith("st "):
        p_points = 50

    elif m_dismissal == "lbw" and player_data["dismissal"].startswith("lbw "):
        p_points = 50

    elif m_dismissal == "runout" and player_data["dismissal"].startswith("run out "):
        p_points = 100

    else:
        p_points = 0

    return p_points


def calculate_points_prediction_6(prediction_6, scoreboard_data):

    p_points = 0
    if len(scoreboard_data["Innings1"][2]) > 1:

        innings_1_team = ""
        innings_2_team = ""

        for t in teams.keys():
            try:

                if t in scoreboard_data["Innings1"][2]["team"].lower():
                    innings_1_team = teams[t]

                elif t in scoreboard_data["Innings2"][2]["team"].lower():
                    innings_2_team = teams[t]
            except:
                return p_points

        if innings_1_team == "" or innings_2_team == "":
            return p_points

        sixes_comp = {innings_1_team: 0, innings_2_team: 0}

        sixes_comp[innings_1_team] = get_sixes(1, scoreboard_data)
        sixes_comp[innings_2_team] = get_sixes(2, scoreboard_data)

        print("SIXES DATA: ===", sixes_comp)

        if prediction_6 == innings_1_team and sixes_comp[innings_1_team] >= sixes_comp[innings_2_team]:
            p_points = 100

        elif prediction_6 == innings_2_team and sixes_comp[innings_2_team] >= sixes_comp[innings_1_team]:
            p_points = 100

        else:
            p_points = 0

    return p_points


def get_sixes(innings, scoreboard_data):

    no_of_sixes = 0

    for batter in scoreboard_data["Innings"+str(innings)][0]["Batsman"]:

        no_of_sixes += int(batter["sixes"])

    return no_of_sixes


def calculate_points_prediction_4(prediction_4, scorecard_data):
    # ["< 120","121 - 140","141 - 160","161 - 180","181 - 200","200+"]
    p_points = 0

    if len(scorecard_data["Innings1"][2]) > 1:

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


def calculate_points_prediction_5(prediction_5, scorecard_data):
    # ["< 120","121 - 140","141 - 160","161 - 180","181 - 200","200+"]
    p_points = 0

    if len(scorecard_data["Innings2"][2]) > 1:

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


def calculate_points_prediction_2(prediction_2, scorecard_data):
    p_points = 0
    for player_data in scorecard_data["Innings1"][1]["Bowlers"]:

        if prediction_2.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_2.lower():

            p_points = calculate_points_for_wickets(
                player_data, scorecard_data)
            # player_points[prediction_1] = p_points
            return p_points

       

    for player_data in scorecard_data["Innings2"][1]["Bowlers"]:

        if prediction_2.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_2.lower():

            p_points = calculate_points_for_wickets(
                player_data, scorecard_data)
            # player_points[prediction_1] = p_points
            return p_points

    # CHECKING MAPPINGS===================================================

    if prediction_2 in player_mappings:

        prediction_2 = player_mappings[prediction_2]

        for player_data in scorecard_data["Innings1"][1]["Bowlers"]:

            if prediction_2.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_2.lower():

                p_points = calculate_points_for_wickets(
                    player_data, scorecard_data)
                # player_points[prediction_1] = p_points
                return p_points
        for player_data in scorecard_data["Innings2"][1]["Bowlers"]:

            if prediction_2.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_2.lower():

                p_points = calculate_points_for_wickets(
                    player_data, scorecard_data)
                # player_points[prediction_1] = p_points
                return p_points

        

    return p_points


def calculate_points_for_wickets(player_data, scorecard_data):
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


def calculate_points_prediction_1(prediction_1, scorecard_data):
    # player_points = {}
    p_points = 0

    for player_data in scorecard_data["Innings1"][0]["Batsman"]:

        if prediction_1.lower().strip() in player_data["name"].lower().replace('(c)', '').replace('(wk)', '').strip() or player_data["name"].lower().replace('(c)', '').replace('(wk)', '').strip() in prediction_1.lower():

            p_points = calculate_points_for_runs(player_data, scorecard_data)
            # player_points[prediction_1] = p_points
            return p_points

        
    for player_data in scorecard_data["Innings2"][0]["Batsman"]:

        if prediction_1.lower().strip() in player_data["name"].lower().replace('(c)', '').replace('(wk)', '').strip() or player_data["name"].lower().replace('(c)', '').replace('(wk)', '').strip() in prediction_1.lower():

            p_points = calculate_points_for_runs(player_data, scorecard_data)
            # player_points[prediction_1] = p_points
            return p_points

    # CALCULATE MAPPINGS===========

    if prediction_1 in player_mappings:

        prediction_1 = player_mappings[prediction_1]

        for player_data in scorecard_data["Innings1"][0]["Batsman"]:

            if prediction_1.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_1.lower():

                p_points = calculate_points_for_runs(
                    player_data, scorecard_data)
                # player_points[prediction_1] = p_points
                return p_points
        for player_data in scorecard_data["Innings2"][0]["Batsman"]:

            if prediction_1.lower().strip() in player_data["name"].lower().strip() or player_data["name"].lower() in prediction_1.lower():

                p_points = calculate_points_for_runs(
                    player_data, scorecard_data)
                # player_points[prediction_1] = p_points
                return p_points

    return p_points


def calculate_points_for_runs(player_data, scorecard_data):

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


@app.route("/delete_user", methods=["GET", "POST"])
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
            if user['username'] == username and user['password'] == password:
                break
        else:
            flash("User not found or user/password incorrect")
            return render_template("failure1.html")
        res1 = client["player_data"]["per_match_data"]
        res1.update_many({}, {"$unset": {"player_predictions."+username: 1}})
        res.delete_one({"username": username})
        flash(username+" Deleted")
        return render_template("failure1.html")


if __name__ == "__main__":
    print("* Loading..."+"please wait until server has fully started")

    make_connections()

    app.run(host='0.0.0.0', port=5000, debug=True)
