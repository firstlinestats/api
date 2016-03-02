
import constants


def get_player_type(given):
    for option in constants.playerTypes:
        if option[1] == given:
            return option[0]
    return 0


def init_player():
    numberkeys = ["g", "a1", "a2", "cf", "ca", "ff", "fa", "g+-", "fo_w", "fo_l",
    "hit+", "hit-", "pn+", "pn-", "gf", "ga", "sf", "sa", "msf", "msa", "bsf", "bsa",
    "icf", "save", "ab", "bk", "ihsc", "isc", "zso", "zsd", "scf", "sca", "sh", "ms"]
    strkeys = ["name", "position", "team"]
    player = {}
    for n in numberkeys:
        player[n] = 0
    for n in strkeys:
        player[n] = ""
    return player


def init_goalie():
    numberkeys = ["gu", "su", "gl", "sl", "gm", "sm", "gh", "sh", "toi"]
    strkeys = ["name", "position", "team", "teamAbbr"]
    player = {}
    for n in numberkeys:
        player[n] = 0
    for n in strkeys:
        player[n] = ""
    return player


def init_team():
    numberkeys = ["gf", "sf", "msf", "bsf", "cf", "scf", "hscf", "zso", "hit+", "pn",
        "fo_w", "toi"]
    strkeys = []
    team = {}
    for n in numberkeys:
        team[n] = 0
    for n in strkeys:
        team[n] = ""
    return team


def calc_sa(sas, seconds):
    sas.append({"seconds": seconds, "value": len(sas) + 1})


def findPPGoal(eventcount, teampp, teamgoal):
    for pp in eventcount[teampp]:
        start = pp["seconds"]
        end = pp["seconds"] + pp["length"]
        for goal in eventcount[teamgoal]:
            if goal["seconds"] > start and goal["seconds"] < end:
                pp["length"] = goal["seconds"] - start
    return eventcount
