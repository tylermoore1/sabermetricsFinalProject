from flask import Flask, render_template, request, jsonify, url_for
import json

import pandas as pd
from pybaseball.lahman import *

from pybaseball.retrosheet import *

app = Flask(__name__)

year = ['park_factor_2014','park_factor_2015','park_factor_2016']

class Team(object):
    teamID = ""
    teamName = ""
    park_factor = 0
    score_adjusted = 0
    OBP_adjusted = 0
    SLG_adjusted = 0
    Super_Score = 0

    # The class "constructor" - It's actually an initializer
    def __init__(self, teamID, teamName, park_factor, score_adjusted, OBP_adjusted, SLG_adjusted, Super_Score):
        self.teamID = teamID
        self.teamName = teamName
        self.park_factor = park_factor
        self.score_adjusted = score_adjusted
        self.OBP_adjusted = OBP_adjusted
        self.SLG_adjusted = SLG_adjusted
        self.Super_Score = Super_Score

def getAllTeamsInfo(yearID):
    season = 0
    if (yearID == 0):
        season = 2014
    elif (yearID == 1):
        season = 2015
    elif (yearID == 2):
        season = 2016
    games = season_game_logs(season)

    park_factor = pd.read_csv("datasets/parkfactors.csv")

    park_factor = park_factor.rename(columns={'teamID':'home_team'})

    #add OBP for home and away teams
    games['home_OBP'] = ((games['home_hits'] + games['home_bb'] + games['home_hbp']) /
                        (games['home_abs'] + games['home_bb'] + games['home_hbp'] + games['home_sac_flies']))
    games['visiting_OBP'] = ((games['visiting_hits'] + games['visiting_bb'] + games['visiting_hbp']) /
                        (games['visiting_abs'] + games['visiting_bb'] + games['visiting_hbp'] + games['visiting_sac_flies']))

    #add SLG for home and away games
    games['home_SLG'] = ((games['home_hits'] + games['home_doubles'] + (2 * games['home_triples']) + (3 * games['home_homeruns']))
                         / games['home_abs'])
    games['visiting_SLG'] = ((games['visiting_hits'] + games['visiting_doubles'] + (2 * games['visiting_triples']) + (3 * games['visiting_homeruns']))
                         / games['visiting_abs'])

    #need to merge home team park factor into retrosheet data so that we can use it to calculate adjuste runs
    gamesWithParkFactor = pd.merge(games, park_factor[['home_team','name', year[yearID]]], on='home_team', how='left')

    #now need to calculate home and away scores based on the park factor they are playing in
    gamesWithParkFactor['reverse_park_factor_2016'] = ((1 - gamesWithParkFactor[year[yearID]]) + 1)

    gamesWithParkFactor['home_score_adjusted'] = gamesWithParkFactor['home_score'] * gamesWithParkFactor['reverse_park_factor_2016']
    gamesWithParkFactor['visiting_score_adjusted'] = gamesWithParkFactor['visiting_score'] * gamesWithParkFactor['reverse_park_factor_2016']

    homeTeamsAdjustedScores = gamesWithParkFactor.groupby(['home_team','name']).agg({year[yearID]:'mean','home_score':'mean','home_score_adjusted':'mean'}).reset_index()
    visitingTeamsAdjustedScores = gamesWithParkFactor.groupby('visiting_team').agg({'visiting_score':'mean','visiting_score_adjusted':'mean'}).reset_index()

    adjustedScores = pd.merge(homeTeamsAdjustedScores, visitingTeamsAdjustedScores.rename(columns={'visiting_team':'home_team'}), on='home_team', how='left')

    adjustedScores['score_adjusted'] = (adjustedScores['home_score_adjusted'] + adjustedScores['visiting_score_adjusted']) / 2

    #print (adjustedScores.head(30).sort_values(by='score_adjusted', ascending=False))

    #do adjusted OBP
    gamesWithParkFactor['home_OBP_adjusted'] = gamesWithParkFactor['home_OBP'] * gamesWithParkFactor['reverse_park_factor_2016']
    gamesWithParkFactor['visiting_OBP_adjusted'] = gamesWithParkFactor['visiting_OBP'] * gamesWithParkFactor['reverse_park_factor_2016']

    homeTeamsAdjustedOBP = gamesWithParkFactor.groupby('home_team').agg({year[yearID]:'mean','home_OBP':'mean','home_OBP_adjusted':'mean'}).reset_index()
    visitingTeamsAdjustedOBP = gamesWithParkFactor.groupby('visiting_team').agg({'visiting_OBP':'mean','visiting_OBP_adjusted':'mean'}).reset_index()

    adjustedOBP = pd.merge(homeTeamsAdjustedOBP, visitingTeamsAdjustedOBP.rename(columns={'visiting_team':'home_team'}), on='home_team', how='left')

    adjustedOBP['OBP_adjusted'] = (adjustedOBP['home_OBP_adjusted'] + adjustedOBP['visiting_OBP_adjusted']) / 2

    #print (adjustedOBP.head(30).sort_values(by='OBP_adjusted', ascending=False))

    #do adjusted SLG
    gamesWithParkFactor['home_SLG_adjusted'] = gamesWithParkFactor['home_SLG'] * gamesWithParkFactor['reverse_park_factor_2016']
    gamesWithParkFactor['visiting_SLG_adjusted'] = gamesWithParkFactor['visiting_SLG'] * gamesWithParkFactor['reverse_park_factor_2016']

    homeTeamsAdjustedSLG = gamesWithParkFactor.groupby('home_team').agg({year[yearID]:'mean','home_SLG':'mean','home_SLG_adjusted':'mean'}).reset_index()
    visitingTeamsAdjustedSLG = gamesWithParkFactor.groupby('visiting_team').agg({'visiting_SLG':'mean','visiting_SLG_adjusted':'mean'}).reset_index()

    adjustedSLG = pd.merge(homeTeamsAdjustedSLG, visitingTeamsAdjustedSLG.rename(columns={'visiting_team':'home_team'}), on='home_team', how='left')

    adjustedSLG['SLG_adjusted'] = (adjustedSLG['home_SLG_adjusted'] + adjustedSLG['visiting_SLG_adjusted']) / 2

    #print (adjustedSLG.head(30).sort_values(by='SLG_adjusted', ascending=False))

    #now need to merge all of the data together to get super score
    mergedData = pd.merge(adjustedScores, adjustedOBP[['home_team','OBP_adjusted']],on=['home_team'],how='inner')
    mergedData = pd.merge(mergedData, adjustedSLG[['home_team','SLG_adjusted']],on=['home_team'],how='inner')
    runMean=mergedData['score_adjusted'].mean()
    obpMean=mergedData['OBP_adjusted'].mean()
    slgMean=mergedData['SLG_adjusted'].mean()
    obpFactor=runMean/obpMean
    slgFactor=runMean/slgMean
    mergedData['Super_Score']=mergedData['score_adjusted']+obpFactor*mergedData['OBP_adjusted']+slgFactor*mergedData['SLG_adjusted']
    mergedData=mergedData.sort_values(by=['Super_Score'],ascending=False)
    # print (mergedData)

    return mergedData

def listTeams(yearID):
    mergedData = getAllTeamsInfo(yearID)

    listOfTeams = []
    for index, row in mergedData.iterrows():
        teamID = row['home_team']
        teamName = row['name']
        park_factor = row[year[yearID]]
        score_adjusted = row['score_adjusted']
        OBP_adjusted = row['OBP_adjusted']
        SLG_adjusted = row['SLG_adjusted']
        Super_Score = row['Super_Score']

        newTeam = Team(teamID, teamName, park_factor, score_adjusted, OBP_adjusted, SLG_adjusted, Super_Score)
        listOfTeams.append(newTeam.__dict__)

    return listOfTeams

def searchTeam(teamName):
    yearID = 2
    mergedData = getAllTeamsInfo(yearID)

    teamName = teamName.lower()
    teamName = teamName.title()
    print (teamName)
    specificTeam = mergedData.loc[(mergedData['name'] == teamName)]
    #specificTeam = specificTeam.to_json()

    listOfTeams = []
    for index, row in specificTeam.iterrows():
        teamID = row['home_team']
        teamName = row['name']
        park_factor = row[year[yearID]]
        score_adjusted = row['score_adjusted']
        OBP_adjusted = row['OBP_adjusted']
        SLG_adjusted = row['SLG_adjusted']
        Super_Score = row['Super_Score']

        newTeam = Team(teamID, teamName, park_factor, score_adjusted, OBP_adjusted, SLG_adjusted, Super_Score)
        listOfTeams.append(newTeam.__dict__)

    return listOfTeams


#this is for the page to load for the first time
@app.route('/', methods = ['GET'])
def evaluateteams():
    #result = request.form.get('Name')
    return render_template('index.html')

#this is to load a certain teams data to show on webpage
@app.route('/search', methods = ['GET'])
def search():
    teamName = request.args.get('teamName')
    listOfTeams = searchTeam(teamName)
    return json.dumps(listOfTeams)

#this is to load all team data to show on webpage
@app.route('/teams', methods = ['GET'])
def teams():
    filterYear = request.args.get('yearID')
    if (filterYear == 'idFilter2014'):
        yearID = 0
    elif (filterYear == 'idFilter2015'):
        yearID = 1
    elif (filterYear == 'idFilter2016'):
        yearID = 2

    listOfTeams = listTeams(yearID);
    #player = Team('tyler',19,0)
    return json.dumps(listOfTeams)


if __name__ == '__main__':
    app.run(debug=True)
