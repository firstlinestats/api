import gzip
import json
import pytz
import MySQLdb
import datetime
from StringIO import StringIO
from urllib2 import Request, urlopen, URLError

headers = {
    "User-Agent" : "Mozilla/5.0 (X11; U; Linux i686; " + \
        "en-US; rv:1.9.2.24) Gecko/20111107 " + \
        "Linux Mint/9 (Isadora) Firefox/3.6.24",
}

BASE_URL = "http://statsapi.web.nhl.com/api/"
STANDINGS = BASE_URL + "v1/standings"
SEASONS = BASE_URL + "v1/seasons"

import cred


def connect_mysql():
    cnx = MySQLdb.connect(cred.HOST, cred.USER, cred.PASSWORD,
        cred.DB_NAME)
    return cnx


def get_standings(date=None):
    url = STANDINGS
    if date is not None:
        url += "?date=" + date
    return get_url(url)


def get_seasons():
    url = SEASONS
    return get_url(url)


def get_url(url):
    request = Request(url, headers=headers)
    request.add_header('Accept-encoding', 'gzip')
    try:
        response = urlopen(request)
        if response.info().get('Content-Encoding') == 'gzip':
            buf = StringIO( response.read())
            f = gzip.GzipFile(fileobj=buf)
            html = f.read()
        else:
            html = response.read()
    except URLError, e:
        print e
        return "{}"
    return html


def findStandings(season):
    cnx = connect_mysql()
    cursor = cnx.cursor()
    tdate = datetime.datetime.now(pytz.timezone("EST")).strftime("%Y-%m-%d")
    j = json.loads(get_standings())
    add_standing = ("INSERT INTO team_seasonstats"
        "(team_id, season, goalsAgainst, goalsScored, "
        "points, gamesPlayed, wins, losses, ot, date, streakCode) "
        "VALUES (%(team_id)s, %(season)s, %(goalsAgainst)s,"
        "%(goalsScored)s, %(points)s, %(gamesPlayed)s, %(wins)s,"
        "%(losses)s, %(ot)s, '%(date)s', '%(streakCode)s')")
    for record in j["records"]:
        division = record["division"]["name"][0]
        conference = record["division"]["name"][0]
        for team in record["teamRecords"]:
            stat = {}
            stat["team_id"] = team["team"]["id"]
            stat["season"] = season
            try:
                stat["goalsAgainst"] = team["goalsAgainst"]
                stat["goalsScored"] = team["goalsScored"]
            except:
                stat["goalsAgainst"] = None
                stat["goalsScored"] = None
            stat["points"] = team["points"]
            stat["gamesPlayed"] = team["gamesPlayed"]
            stat["wins"] = team["leagueRecord"]["wins"]
            stat["losses"] = team["leagueRecord"]["losses"]
            stat["ot"] = team["leagueRecord"]["ot"]
            stat["date"] = tdate
            try:
                stat["streakCode"] = team["streak"]["streakCode"]
            except:
                stat["streakCode"] = None
            cursor.execute((add_standing % stat))
    cnx.commit()
    cursor.close()
    cnx.close()


if __name__ == "__main__":
    seasons = json.loads(get_seasons())
    seasons = [x["seasonId"] for x in seasons["seasons"]]
    findStandings(max(seasons))
