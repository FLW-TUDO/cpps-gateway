#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time


class Task:
    def __init__(self,
                 task_id: int,
                 date: float,
                 state: str,
                 configuration: dict
                 ):
        self.task_id = task_id
        self.date = date
        self.state = state
        self.configuration = configuration
        self.empty_klt_phyaddr = 0
        self.empty_klt_energy = 0
        self.empty_klt_home_position = None
        self.robot = {}
        self.task_end_time = None
        self.product_variant = self.get_product_variant()
        self.stage1 = ''
        self.stage2 = ''
        self.k01 = {}
        self.k02 = {}
        self.k03 = {}
        self.k04 = {}
        self.k05 = {}
        self.k06 = {}
        self.k07 = {}
        self.k08 = {}
        self.k09 = {}

    def get_product_variant(self):
        product_variant = {}
        if self.configuration:
            try:
                product_variant = str(self.configuration['engine']) + '_' + \
                                  self.configuration['color_topdown'] + '_' + \
                                  self.configuration['color_drone'] + '_' + \
                                  self.configuration['color_mounting']
            except KeyError:
                return product_variant
        return product_variant

    @staticmethod
    def from_dict(source):
        order = Task(
            task_id=int(source['task_id']),
            # date=float(source['date']),
            date=time.time(),
            state=source['state'],
            configuration=dict(source['configuration'])
        )
        return order

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'date': self.date,
            'state': self.state,
            'configuration': self.configuration,
            'empty_klt_phyaddr': self.empty_klt_phyaddr,
            'empty_klt_energy': self.empty_klt_energy,
            'empty_klt_home_position': self.empty_klt_home_position,
            'robot': self.robot,
            'task_end_time': self.task_end_time,
            'product_variant': self.product_variant,
            'stage1': self.stage1,
            'stage2': self.stage2,
            'k01': self.k01,
            'k02': self.k02,
            'k03': self.k03,
            'k04': self.k04,
            'k05': self.k05,
            'k06': self.k06,
            'k07': self.k07,
            'k08': self.k08,
            'k09': self.k09
        }
