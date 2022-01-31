#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class Entry:
    def __init__(self,
                 id_cycle: str,
                 id_task: int,
                 id_labor_process: str,
                 start_time: float,
                 time_slot_length: float
                 ):
        """
        :param id_cycle: (str)
        :param id_task: (int)
        :param id_labor_process: (str)
        :param start_time: (float)
        :param time_slot_length: (float)
        """
        self.id_cycle = id_cycle
        self.id_task = id_task
        self.id_labor_process = id_labor_process
        self.start_time = start_time
        self.time_slot_length = time_slot_length

    def to_dict(self):
        """
        :return result: (dict)
            id_task: (int)
            id_labor_process: (str)
            desired_availability_date: (float)
            time_slot_length: (float)
        """
        result = {
            'id_cycle': self.id_cycle,
            'id_task': self.id_task,
            'id_labor_process': self.id_labor_process,
            'desired_availability_date': self.start_time,
            'time_slot_length': self.time_slot_length
        }
        return result


class Node:
    def __init__(self, entry, prev, nex):
        """
        :param entry: (Entry)
            The value of the Node as entry object.
        :param prev: (Node)
            The previous node. None if head of the list.
        :param nex: (Node)
            The next node. None if tail of the list.
        """
        self.entry = entry
        self.prev = prev
        self.next = nex

    def has_next(self):
        """
        :return: (bool)
            Return true if the current node has an successor, else False.
        """
        if self.next is None:
            return False
        else:
            return True

    def has_prev(self):
        """
        :return: (bool)
            Return true if the current node has an successor, else False.
        """
        if self.prev is None:
            return False
        else:
            return True


class Calendar:
    def __init__(self):
        self.head = None
        self.tail = None

    def append(self, new_entry: Entry, rotating_time: int = 5):
        """
        :param new_entry: (Entry)
            New calendar entry that define the start time.
        :return: (Entry)
            Returns an entry object with new availability start time.
        """
        new_node = Node(new_entry, None, None)
        temp_iterator = None
        iterator = self.head
        # Falls die Doppeltverketteteliste keine Einträge enthaelt
        if iterator is None:
            self.head = new_node
            self.tail = new_node
            return new_node.entry
        # Falls nur ein Eintrag in der Liste exestiert
        elif iterator == self.tail:
            if iterator.entry.id_cycle == new_node.entry.id_cycle:
                # Wird danach eingehangen
                append_before = False
            else:
                new_node_end_time = new_node.entry.start_time + new_node.entry.time_slot_length + rotating_time
                # Am Anfang der Liste einfuegen, falls Endzeitpunkt des neuen Eintrags kleiner ist
                if iterator.entry.start_time > new_node_end_time:
                    append_before = True
                # Sonst am Ende der Liste einfuegen, ggf Startzeit anpassen
                else:
                    iterator_end_time = iterator.entry.start_time + iterator.entry.time_slot_length + rotating_time
                    if iterator_end_time > new_node.entry.start_time:
                        new_start_time = iterator_end_time
                        new_node.entry.start_time = new_start_time
                    append_before = False
            if append_before:
                self.head = new_node
                self.head.next = self.tail
                self.tail.prev = self.head
                self.tail.next = None
            else:
                self.tail = new_node
                self.tail.prev = self.head
                self.head.next = self.tail
                self.head.prev = None
            return new_node.entry
        # Es existieren mehrere Einträge im Kalender
        else:
            # Iteriert über die Liste und sucht passenden Slot
            while iterator.has_next():
                # Eintrag mit gleicher Zyklus Id gefunden
                if iterator.entry.id_cycle == new_node.entry.id_cycle:
                    if temp_iterator is None:
                        if iterator == self.head:
                            temp_iterator = iterator
                        else:
                            temp_iterator = iterator.prev
                    iterator = iterator.next
                    continue
                # Eintrag mit unterschiedlicher Zyklus Id
                else:
                    new_node_end_time = new_node.entry.start_time + new_node.entry.time_slot_length + rotating_time
                    # Vorlaufig passende Position gefunden
                    if iterator.entry.start_time > new_node_end_time:
                        if temp_iterator is None:
                            prev_iterator = iterator.prev
                        else:
                            if temp_iterator == self.head:
                                prev_iterator = None
                            else:
                                prev_iterator = temp_iterator
                            temp_iterator = None
                        if prev_iterator is None:
                            new_node.prev = iterator.prev
                            new_node.next = iterator
                            iterator.prev = new_node
                            self.head = new_node
                            return new_node.entry
                        else:
                            prev_end_time = prev_iterator.entry.start_time + prev_iterator.entry.time_slot_length + \
                                            rotating_time
                            # Zeitslot passt in die Luecke
                            if prev_end_time <= new_node.entry.start_time:
                                new_node.prev = iterator.prev
                                new_node.next = iterator
                                iterator.prev.next = new_node
                                iterator.prev = new_node
                                return new_node.entry
                            # Startzeitpunkt muss angepasst werden, falls möglich
                            else:
                                new_start_time = prev_end_time
                                new_end_time = new_start_time + new_node.entry.time_slot_length
                                if new_end_time < iterator.entry.start_time:
                                    new_node.entry.start_time = new_start_time
                                    new_node.prev = iterator.prev
                                    new_node.next = iterator
                                    iterator.prev.next = new_node
                                    iterator.prev = new_node
                                    return new_node.entry
                    else:
                        temp_iterator = None
                iterator = iterator.next
            # Neuer Eintrag wird ans Ende der Liste hinzugefuegt
            else:
                # Eintrag mit gleicher Zyklus Id gefunden
                if iterator.entry.id_cycle == new_node.entry.id_cycle:
                    if temp_iterator is None:
                        prev_iterator = iterator.prev
                    else:
                        if temp_iterator == self.head:
                            prev_iterator = None
                        else:
                            prev_iterator = temp_iterator
                        temp_iterator = Node
                    if prev_iterator is not None:
                        prev_end_time = prev_iterator.entry.start_time + prev_iterator.entry.time_slot_length + \
                                        rotating_time
                        # Startzeitpunkt muss angepasst werden
                        if prev_end_time > new_node.entry.start_time:
                            new_start_time = prev_end_time
                            new_node.entry.start_time = new_start_time
                    new_node.prev = iterator
                    iterator.next = new_node
                    self.tail = new_node
                    return new_node.entry
                # Eintrag mit unterschiedlicher Zyklus Id
                else:
                    new_node_end_time = new_node.entry.start_time + new_node.entry.time_slot_length + rotating_time
                    if iterator.entry.start_time > new_node_end_time:
                        if temp_iterator is None:
                            prev_iterator = iterator.prev
                        else:
                            if temp_iterator == self.head:
                                prev_iterator = None
                            else:
                                prev_iterator = temp_iterator
                        temp_iterator = Node
                        if prev_iterator is None:
                            new_node.prev = iterator.prev
                            new_node.next = iterator
                            iterator.prev = new_node
                            self.head = new_node
                            return new_node.entry
                        else:
                            prev_end_time = prev_iterator.entry.start_time + prev_iterator.entry.time_slot_length + \
                                            rotating_time
                            # Zeitslot passt in die Luecke
                            if prev_end_time <= new_node.entry.start_time:
                                new_node.prev = iterator.prev
                                new_node.next = iterator
                                iterator.prev.next = new_node
                                iterator.prev = new_node
                                return new_node.entry
                            # Startzeitpunkt muss angepasst werden, falls möglich
                            else:
                                new_start_time = prev_end_time
                                new_end_time = new_start_time + new_node.entry.time_slot_length + rotating_time
                                if new_end_time < iterator.entry.start_time:
                                    new_node.entry.start_time = new_start_time
                                    new_node.prev = iterator.prev
                                    new_node.next = iterator
                                    iterator.prev.next = new_node
                                    iterator.prev = new_node
                                    return new_node.entry
                    iterator_end_time = iterator.entry.start_time + iterator.entry.time_slot_length + rotating_time
                    # Startzeitpunkt muss angepasst werden
                    if iterator_end_time >= new_node.entry.start_time:
                        new_start_time = iterator_end_time
                        new_node.entry.start_time = new_start_time
                    new_node.prev = iterator
                    iterator.next = new_node
                    self.tail = new_node
                    return new_node.entry

    # This function deletes all entries with the same task id and labor process id
    def delete(self,
               id_task: str,
               id_labor_process: str,
               print_out: bool
               ) -> int:
        count = 0
        iterator = self.head
        if iterator is None:
            # print('    No entry in the list found') if print_out else ''
            return count
        else:
            if iterator == self.tail:
                # print('    Just one entry in the list') if print_out else ''
                if iterator.entry.id_task == id_task and \
                        iterator.entry.id_labor_process == id_labor_process:
                    # print('    Find same entry') if print_out else ''
                    self.head = None
                    self.tail = None
                    return count + 1
                else:
                    # print('    Dont find same entry') if print_out else ''
                    return count
            else:
                while iterator.has_next():
                    # print('    hasNext: ' + str(iterator.has_next()))
                    # print('    hasPrev: ' + str(iterator.has_prev()))
                    # print('    More then one entry') if print_out else ''
                    if iterator.entry.id_task == id_task and iterator.entry.id_labor_process == id_labor_process:
                        # print('    Find same entry') if print_out else ''
                        if iterator.prev is None:
                            # print('    First entry delete') if print_out else ''
                            self.head = iterator.next
                            iterator.next.prev = None
                            count += 1
                        else:
                            # print('    Middle entry delete') if print_out else ''
                            iterator.prev.next = iterator.next
                            iterator.next.prev = iterator.prev
                            count += 1
                    iterator = iterator.next
                else:
                    if iterator.entry.id_task == id_task and iterator.entry.id_labor_process == id_labor_process:
                        # print('    Find same entry') if print_out else ''
                        # print('    Last entry delete') if print_out else ''
                        # print('    hasNext: ' + str(iterator.has_next()))
                        # print('    hasPrev: ' + str(iterator.has_prev()))
                        if iterator.prev is None:
                            self.head = self.tail = None
                        else:
                            iterator.prev.next = None
                            self.tail = iterator.prev
                        count += 1
                return count

    def update(self,
               id_task: int,
               id_labor_process: str,
               new_start_time: float,
               new_time_slot_length: float
               ) -> Entry or None:
        iterator = self.head
        if iterator is not None:
            if iterator == self.tail:
                if iterator.entry.id_task == id_task and iterator.entry.id_labor_process == id_labor_process:
                    iterator.entry.start_time = new_start_time
                    iterator.entry.time_slot_length = new_time_slot_length
                    return iterator.entry
                else:
                    return None
            else:
                while iterator.has_next():
                    if iterator.entry.id_task == id_task and iterator.entry.id_labor_process == id_labor_process:
                        iterator.entry.start_time = new_start_time
                        iterator.entry.time_slot_length = new_time_slot_length
                        return iterator.entry
                    iterator = iterator.next
                else:
                    if iterator.entry.id_task == id_task and iterator.entry.id_labor_process == id_labor_process:
                        iterator.entry.start_time = new_start_time
                        iterator.entry.time_slot_length = new_time_slot_length
                        return iterator.entry
                    else:
                        return None
        return None

    def get_entry(self,
                  id_task: int,
                  id_labor_process: str
                  ):
        if self.head == self.tail is None:
            return None
        if self.head == self.tail:
            if self.head.entry.id_task == id_task and self.head.entry.id_labor_process == id_labor_process:
                return self.head.entry
            else:
                return None
        iterator = self.head
        while iterator.has_next():
            if iterator.entry.id_task == id_task and iterator.entry.id_labor_process == id_labor_process:
                return iterator.entry
            iterator = iterator.next
        else:
            if iterator.entry.id_task == id_task and iterator.entry.id_labor_process == id_labor_process:
                return iterator.entry
        return None

    def to_dict_list(self) -> list:
        iterator = self.head
        result = []
        if iterator is not None:
            while iterator.has_next():
                result.append(iterator.entry.to_dict())
                iterator = iterator.next
            else:
                result.append(iterator.entry.to_dict())
        return result


class Workstation(object):
    """
    skills = [
        {
            'skill': string,
            'period_time': seconds
        },
        ...
    ]
    """

    def __init__(self,
                 workstation_id="",
                 vicon_id="",
                 skills=None,
                 costs=0.0,
                 active=False
                 ):
        if skills is None:
            skills = []
        self._workstation_id = workstation_id
        self._vicon_id = vicon_id
        self._skills = skills  # A list of skills from AV1 to AV10
        self._costs = costs
        self._active = active
        self._blocked = True
        self._calendar = Calendar()

    def attributes_to_dict(self) -> dict:
        return {
            'workstation_id': self._workstation_id,
            'vicon_id': self._vicon_id,
            'skills': self._skills,
            'labor_costs': self._costs,
            'active': self._active,
            'blocked': self._blocked,
            'calendar': self._calendar.to_dict_list()
        }

    def get_entry(self,
                  id_task: int,
                  id_labor_process: str
                  ):
        return self._calendar.get_entry(id_task=id_task, id_labor_process=id_labor_process)

    def get_workstation_id(self) -> str:
        return self._workstation_id

    def get_vicon_id(self) -> str:
        return self._vicon_id

    def get_skills(self) -> list:
        return self._skills

    def get_skill(self, searched_skill: str) -> dict:
        for skill in self._skills:
            if skill['skill'] == searched_skill:
                return skill
        return {}

    def has_skill(self, searched_skill: str) -> bool:
        for skill in self._skills:
            if skill['skill'] == searched_skill:
                return True
        return False

    def get_skill_time(self, searched_skill: str) -> float:
        for skill in self._skills:
            if skill['skill'] == searched_skill:
                return float(skill['time'])
        return 0.0

    def get_costs(self) -> float:
        return self._costs

    def get_calendar(self) -> list:
        return self._calendar.to_dict_list()

    def set_skills(self, new_skills: list) -> bool:
        if new_skills is not None and isinstance(new_skills, list):
            self._skills = new_skills
            return True
        return False

    def set_costs(self, new_costs: float) -> bool:
        if new_costs is not None and isinstance(new_costs, float):
            self._costs = new_costs
            return True
        return False

    def activate(self) -> bool:
        self._active = True
        return self._active

    def deactivate(self) -> bool:
        self._active = False
        return self._active

    def is_active(self) -> bool:
        return self._active

    def block(self) -> bool:
        self._blocked = True
        return self._blocked

    def unblock(self) -> bool:
        self._blocked = False
        return self._blocked

    def reservation(self,
                    id_cycle: str,
                    id_task: int,
                    id_labor_process: str,
                    desired_start_time: float,
                    desired_skill: str,
                    delta: float
                    ) -> dict:
        """
        :param id_cycle: (str)
        :param id_task: (int)
        :param id_labor_process: (str)
        :param desired_start_time: (dict)
        :param desired_skill: (str)
        :param delta: (float)

        :return: (dict)
            buffer_time: (float)
            id_task: (int)
            id_labor_process: (str)
            costs_workstation: (float)
            desired_availability_date: (float)
            time_slot_length: (float)
            skill_time: (float)
        """
        skill_time = self.get_skill_time(desired_skill)
        buffer_time = skill_time * delta
        time_slot_length = skill_time + buffer_time
        costs_workstation = self._costs * skill_time
        new_calendar_entry = Entry(
            id_cycle=id_cycle,
            id_task=id_task,
            id_labor_process=id_labor_process,
            start_time=desired_start_time,
            time_slot_length=time_slot_length
        )
        desired_availability_date = self._calendar.append(new_entry=new_calendar_entry)
        result = desired_availability_date.to_dict()
        result['buffer_time'] = buffer_time
        result['costs_workstation'] = costs_workstation
        result['skill_time'] = skill_time
        return result

    def reject(self,
               id_task: str,
               id_labor_process: str
               ) -> int:
        result = self._calendar.delete(
            id_task=id_task,
            id_labor_process=id_labor_process,
            print_out=True
        )
        return result

    def book(self,
             id_task: int,
             id_labor_process: str,
             start_time: float,
             ) -> Entry:
        time_slot_length = self.get_skill_time(id_labor_process)
        result = self._calendar.update(id_task=id_task,
                                       id_labor_process=id_labor_process,
                                       new_start_time=start_time,
                                       new_time_slot_length=time_slot_length
                                       )
        return result
