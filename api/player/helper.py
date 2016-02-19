import constants


def getPosition(code):
    for key in constants.skaterPositions:
        if key[0] == code:
            return key[1]
    return code
