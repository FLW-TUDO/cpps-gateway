#!/usr/bin/env python3


import logging

'''
############################################################

Logging requirements

Level	    Numeric value
CRITICAL	50
ERROR	    40
WARNING	    30
INFO	    20
DEBUG	    10
NOTSET	    0
'''

logging.basicConfig(
    filename='_logfile.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s: %(message)s'
)


def log(level, topic, message):
    logging.log(
        level,
        '[{}]: {}'.format('{:<20}'.format(topic), message)
    )
    print('[{}]: {}'.format('{:<20}'.format(topic), message))


'''
############################################################
'''


class shell_font_style:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


'''
############################################################
'''


class Article:
    def __init__(self, aid, number, name, ammount):
        self.aid = aid
        self.number = number
        self.name = name
        self.ammount = ammount

    @staticmethod
    def from_dict(source, ammount):
        article = Article(source['id'], source['number'], source['name'], ammount)
        return article

    def to_dict(self):
        return {
            'id': self.aid,
            'number': self.number,
            'name': self.name,
            'ammount': self.ammount
        }


'''
############################################################
'''


class Order:
    def __init__(self, oid, date, state, articles, stage1, stage2, stage3, stage4, stage5):
        self.oid = int(oid)
        self.date = date
        self.state = state
        self.articles = articles
        self.stage1 = stage1
        self.stage2 = stage2
        self.stage3 = stage3
        self.stage4 = stage4
        self.stage5 = stage5

    @staticmethod
    def from_dict(source):
        order = Order(
            source['id'],
            source['date'],
            source['state'],
            source['articles'],
            source['stage1'],
            source['stage2'],
            source['stage3'],
            source['stage4'],
            source['stage5']
        )
        return order

    def to_dict(self):
        return {
            'id': self.oid,
            'date': self.date,
            'state': self.state,
            'articles': [self.articles],
            'stage1': [self.stage1],
            'stage2': [self.stage2],
            'stage3': [self.stage3],
            'stage4': [self.stage4],
            'stage5': [self.stage5]
        }


'''
############################################################
'''
