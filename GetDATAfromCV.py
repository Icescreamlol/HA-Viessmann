import requests
import sys
import json
import paho.mqtt.client as mqtt
import time
import logging

logPath = "/home/homeassistant/.homeassistant/python_scripts/"
fileName = "CVLog"

logging.basicConfig(level=logging.DEBUG)

logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()

fileHandler = logging.FileHandler("{0}/{1}.log".format(logPath, fileName))
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

def RefreshData():
    List = [0,1,2,3,4,5]

    #SubRoutine for requests
    def GetData(ReqURL, Token):
        #Define Request header
        header = {
         'Authorization':'Bearer ' + Token,
         }
        #Get RequestURL with header
        response = requests.get(ReqURL, headers=header)

        #Return response as JSON
        return response.json();

    #Client ID - Fixed to this numbers    
    client_id = '79742319e39245de5f91d15ff4cac2a8';
    client_secret = '8ad97aceb92c5892e102b093c7c083fa';

    #Viessmann login
    isiwebuserid = 'XXXXXXXXXXXXXXXXXXXXXXXX';   #ViessMann Email
    isiwebpasswd = 'XXXXXXXXXXXXX';              #ViessMann Password

    authorizeURL = 'https://iam.viessmann.com/idp/v1/authorize';
    token_url = 'https://iam.viessmann.com/idp/v1/token';
    apiURLBase = 'https://api.viessmann-platform.io';
    callback_uri = "vicare://oauth-callback/everest";

#Settings to request Autorization Code
    url = authorizeURL + "?client_id=" + client_id + "&scope=openid&redirect_uri=" + callback_uri + "&response_type=code";

    header = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    #Try to get a response, but the requests library does not allow a request URL that does not start with http (ours is: "vicare://oauth-callback/everest")
    try:
        response = requests.post(url, headers=header, auth=(isiwebuserid, isiwebpasswd))
    except Exception as e:
        #capture the error, which contains the code the authorization code and put this in to codestring
        codestring = "{0}".format(str(e.args[0])).encode("utf-8");
        codestring = str(codestring)
        codestring = codestring[codestring.find("?code=")+6:len(codestring)-1]
        #print(codestring)

#Use autorization code to request access_token
    header = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
    }
    data = {
      'client_id':client_id,
      'code':codestring,
      'redirect_uri':callback_uri,
      'grant_type':'authorization_code',
    }
    response = requests.post(token_url, headers=header, data=data, auth=(client_id, client_secret))
    data = response.json()
    Token = data["access_token"]

    
#Use access_token to access data
    #Get installation ID and SERIAL to access data
    apiURL = apiURLBase + '/general-management/installations?expanded=true&'
    data = GetData(apiURL, Token)
    ID = data["entities"][0]["properties"]["id"] #ID of the installation
    SERIAL = data["entities"][0]["entities"][0]["properties"]["serial"] #Serial of installation

    #Combine ID & SERIAL into URL to get data out
    URL = apiURLBase + '/operational-data/installations/' + str(ID) + '/gateways/' + str(SERIAL) + '/devices/0/features/'


    #Gets data out...
    apiURL = URL + 'heating.boiler.sensors.temperature.main'
    data = GetData(apiURL, Token)
    BoilerTemp = data["properties"]["value"]["value"]

    apiURL = URL + 'heating.sensors.temperature.outside'
    data = GetData(apiURL, Token)
    OutsideTemp = data["properties"]["value"]["value"]

    apiURL = URL + 'heating.dhw.temperature'
    data = GetData(apiURL, Token)
    DhwTemp = data["properties"]["value"]["value"]

    apiURL = URL + 'heating.circuits.0.sensors.temperature.room'
    data = GetData(apiURL, Token)
    InsideTemp = data["properties"]["value"]["value"]
    
    apiURL = URL + 'heating.circuits.0.operating.programs.active'
    data = GetData(apiURL, Token)
    boilermode = data["properties"]["value"]["value"]

    apiURL = URL + 'heating.circuits.0.operating.programs.' + boilermode
    data = GetData(apiURL, Token)
    SetTemp = data["properties"]["temperature"]["value"]

    List[0] = BoilerTemp
    List[1] = OutsideTemp
    List[2] = DhwTemp
    List[3] = InsideTemp
    List[4] = boilermode
    List[5] = SetTemp

    return List

while True:
    try:
        #Get Data
        Data = RefreshData()
        #print(Data[0], Data[1], Data[2], Data[3], Data[4], Data[5])
        user='XXXXXXXXXXXXXXXXXXXXXXXXXX'  #MQTT Login
        passw='XXXXXXXXXXXXXXXXXXXXXXXXX'  #MQTT PW
        broker_address="localhost"
        client = mqtt.Client("P1") #create new instance
        client.username_pw_set(user,passw)
        client.connect(broker_address, port=1883) #connect to broker
        MQTT_MSG=json.dumps({"BoilerTemp": Data[0],"OutsideTemp": Data[1],"WaterTemp": Data[2],"InsideTemp":  Data[3],"BoilerMode":  Data[4],"SetTemp":  Data[5]});
        client.publish("CVData",MQTT_MSG)#publish
        print("Updated")
        rootLogger.debug("UPDATED")
        time.sleep(30)
    except:
        print("Failed")
        time.sleep(300)
        rootLogger.debug("FAILED")

