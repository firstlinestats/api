
import constants


def get_player_type(given):
    for option in constants.playerTypes:
        if option[1] == given:
            return option[0]
    return 0


def init_player():
    numberkeys = ["g", "a1", "a2", "p", "cf", "ca", "ff", "fa", "g+-", "fo_w", "fo_l",
    "hit+", "hit-", "pn+", "pn-", "gf", "ga", "sf", "sa", "msf", "msa", "bsf", "bsa",
    "icf", "save", "ab"]
    strkeys = ["name", "position", "team"]
    player = {}
    for n in numberkeys:
        player[n] = 0
    for n in strkeys:
        player[n] = ""
    return player


def init_team():
    numberkeys = ["gf", "sf", "msf", "bsf", "cf", "scf", "hscf", "zso", "hit+", "pn",
        "fo_w", "toi"]
    strkeys = ["team"]
    team = {}
    for n in numberkeys:
        team[n] = 0
    for n in strkeys:
        team[n] = ""
    return team
