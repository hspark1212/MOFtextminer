#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os

import json
from pathlib import Path

import numpy as np
import regex as re
import pandas as pd
import copy

from itertools import combinations, chain, product, repeat

# from gensim.models import Word2Vec

from .utils import word_original, sentence_original, small_molecule_database, Update_list_in_dictionary, cut_paragraph, \
    Get, Check
from .abbreviation import Abbreviation, make_abbreviation
from .unit_database import Unit_database, dimension_analysis
from .preprocessing import DocumentTM
from doc.utils import get_name
import warnings

# In[2]:


unit_dict = {'m2.0g-1.0': {'surface area': {
    'sub_property': {'BET surface area': {'Brunauer-Emmett-Teller': 1, 'BET': 1, 'SBET': 1, 'specific': 0.1},
                     'electrochemical active surface area': {'ECSA': 1},
                     'specific surface area': {'SSA': 1, 'specific': 0.3},
                     'total surface area': {'total': 0.3, 'Stotal': 1},
                     'Langmuir surface area': {'Langmuir': 1, 'specific': 0.1},
                     None: {'area': 0.5, 'areas': 0.5, 'surface': 0.5}},
    'type': 'Character', 'unified': False}},
    'cm3.0g-1.0': {
        'pore volume': {'sub_property': {'total pore volume': {'total': 0.3, 'Vtotal': 1},
                                         None: {'pore': 0.5, 'micropore': 0.5,
                                                'mesopore': 0.5, 'volume': 0.5,
                                                'volumes': 0.5}},
                        'type': 'Character', 'unified': False}},

    'K1.0': {
        'Temperature': {'sub_property': {None: None}, 'type': 'Condition', 'unified': True},
        'Melting point': {'sub_property': {None: {'MP': 1, 'mp': 1, 'melting': 1, 'm.p': 1,
                                                  'M.p': 1, 'm.p.': 1, 'M.p.': 1, 'Mp': 1,
                                                  'M.P.': 1, 'M.P': 1, 'melts': 1, 'melt': 1, 'melted': 1,
                                                  'point': 0.5, 'points': 0.5, 'm.':0.5, 'p.':0.5,
                                                  'M.':0.5, 'P.': 0.5, 'P':0.5, 'p':0.5, 'Tm':1, 'M.pt.':1,
                                                  'm.pt.':1}},
                          'type': 'Reaction', 'unified': True},
        'Boiling point': {
            'sub_property': {None: {'BP': 1, 'bp': 1, 'boiling': 0.5, 'point': 0.5, 'boil': 1, 'boils': 1,
                                    'b.p': 1, 'B.p': 1, 'b.p.': 1, 'B.p.': 1, 'Bp': 1,
                                    'B.P.': 1, 'B.P': 1, 'points': 0.5}},
            'type': 'Reaction', 'unified': True},
        'Decomposition temperature': {
            'sub_property': {None: {'decomposition': 1, 'decomp.': 1, 'decomp': 1, 'dec.': 1, 'decompose': 1,
                                    'decomposes': 1, 'Td': 1, 'decomposed': 1, 'Decomposed': 1, 'd.p.': 1,
                                    'D.p.':1, 'Mp/decomposition': 1, 'mp/decomposition': 1, 'degradation':1,
                                    'D.P.':1, 'Tdec':1, 'Tdec.':1, 'D.':0.5, 'd.':0.5, 'P.':0.5, 'p.':0.5,
                                    'Decomposition': 1, 'Tdecom.':1, 'Tdecom':1, 'Tdecomp.':1, 'Tdecomp':1}},
            'type': 'Reaction', 'unified': True},
        'Thermogravimetric analysis temperature':{
            'sub_property': {None: {'TGA':1, 'tga':1, 'Tga':1, 'thermogravimetric':1, 'TG/DTA':1}},
            'type': None, 'unified': True},
        'crystal data':{
            'sub_property': {None: {'crystal': 0.5, 'data': 0.5, 'crystals':0.5}},
            'type': None, 'unified': True},
    },
    'bar1.0': {
        'Pressure': {'sub_property': {None: None}, 'type': 'Condition', 'unified': True}},
    'Torr1.0': {
        'Pressure': {'sub_property': {None: None}, 'type': 'Condition', 'unified': True}},
    'min1.0': {'Time': {'sub_property': {None: None}, 'type': 'Condition', 'unified': True}},
    'h1.0': {'Time': {'sub_property': {None: None}, 'type': 'Condition', 'unified': True}},

    'sec1.0': {'Time': {'sub_property': {None: None}, 'type': 'Condition', 'unified': True}},

    'g1.0': {'weight': {'sub_property': {None: None}, 'type': 'General', 'unified': True}},
    'mol1.0': {'mole': {'sub_property': {None: None}, 'type': 'General', 'unified': True}},
    'L1.0': {'volume': {'sub_property': {None: None}, 'type': 'General', 'unified': True}},
    'M1.0': {'molar concentration': {'sub_property': {None: None}, 'type': 'General',
                                     'unified': True}},
    'mol1.0L-1.0': {'molar concentration': {'sub_property': {None: None}, 'type': 'General',
                                            'unified': True}},
    '%1.0': {'yield': {'sub_property': {None: {'yield': 1, 'yields': 1, 'Yield': 1, 'Yields': 1}},
                       'type': 'Reaction', 'unified': True}},
}

# In[3]:


keyword_dict = {None: {}}


def make_keyword_dict(unit_dict):
    global keyword_dict

    """Input : unit_dict
    Output : keyword_dict"""

    keyword_dict.clear()
    keyword_dict[None] = {}

    # keyword_dict = {None:{}}
    unit_database = Unit_database()

    for unit, unit_prop in unit_dict.items():

        """ unit : m2.0g-1.0 / unit_prop  = {SA : {sub_property:{prop_name:{keyword:weight}}, type : -, unified : -}}"""

        for prop_name, prop_info in unit_prop.items():
            sub_prop_info = prop_info['sub_property']
            prop_type = prop_info['type']
            unified = prop_info['unified']

            if unified:
                unit_rep = dimension_analysis(unit)
            else:
                unit_rep = unit

            for sub_prop_name, keywords in sub_prop_info.items():
                if isinstance(keywords, dict):
                    for keyword, weight in keywords.items():
                        Update_list_in_dictionary(keyword_dict, keyword,
                                                  (unit_rep, prop_name, sub_prop_name, prop_type, weight))

                else:
                    # keyword_dict[None].append((unit, prop_name, sub_prop_name, prop_type))
                    keyword_dict[None][unit_rep] = (prop_name, sub_prop_name, prop_type, 1)

                # revised when else is needed
    return keyword_dict


keyword_dict = make_keyword_dict(unit_dict)


# In[4]:


class Word():
    def __init__(self, word, database=None):
        self.word = word
        self.group = [self]
        self.keyword = None
        # print (type(database))
        if isinstance(database, dict) and 'abbreviation' in database and word in database.get('abbreviation'):
            self.ABB = list(database['abbreviation'].get_abbreviation(word))
        else:
            self.ABB = None
        self._operation = None
        self.search_keyword()

    def search_keyword(self, word=None, reculsion=False):
        # keyword_list = keyword_dict.get(self.word, None)

        if not isinstance(word, str):
            word = self.word

        if not word:
            return

        elif word in keyword_dict:
            keyword_list = keyword_dict.get(word, None)

        elif re.search(r"_\[.+\]", word):
            words = re.split(r"_\[(?P<sub>.+)\]", word)

            for word_sub in words:
                self.search_keyword(word=word_sub, reculsion=True)

            return

        elif not reculsion and self.ABB:
            for ABB in set(chain.from_iterable(map(lambda abb: abb.split(), self.ABB))):
                self.search_keyword(word=ABB, reculsion=True)

            return

        else:
            return

        if not isinstance(self.keyword, dict):
            self.keyword = {}

        for keyword_tuple in keyword_list:
            unit = keyword_tuple[0]
            prop = keyword_tuple[1]
            sub_prop = keyword_tuple[2]
            prop_type = keyword_tuple[3]
            weight = keyword_tuple[4]
            Update_list_in_dictionary(self.keyword, unit, (prop, sub_prop, prop_type, weight))

    def __repr__(self):
        return self.word

    def __str__(self):
        return self.word

    def set_position(self, position_vector):
        self.position = position_vector
        self.phase = 0

    def distance_with_word(self, word):
        position1 = self.position
        position2 = word.position

        distance = [a - b for a, b in zip(position1, position2)]

        return np.sum(np.abs(distance))

    def __bool__(self):
        return bool(self.word)

    def append_group(self, value):
        if isinstance(value, list):
            for value_each in value:
                self.append_group(value_each)
            return
        elif not isinstance(value, Word):
            raise TypeError(type(value))

        elif value is self:
            return
        self.group.append(value)
        # print ('deps', self.group)


# In[5]:


class Chemical(Word):
    """Chemical.word : hash_code of chemical (ex, -c196842-)
    Chemical.name : name of chemical (ex, HKUST-1)
    Chemical.value : list of class <Value>
    Chemical.group : list of class <Chemical>
    Chemical.cem_type : type of chemical (chemical, ion, element, smallmolecule)
    Chemical.type : type of chemical in reaction (reactant, product, catalyst / anode, cathode, battery / etc.)
    """

    def __init__(self, word, database, _type=None):
        self.word = word
        # self.name = word_original(word, **database)
        self.name = get_name(word, database)
        self.value = []
        self.keyword = None
        self.group = [self]
        self.ABB = None
        self._operation = None

        general_dict = {'c': 'chemical', 'i': 'ion', 'e': 'element', 's': 'smallmolecule'}
        hash_type = re.match(r"[-](?P<type>c|i|e|s)\d{5,6}[-]|-strange(.+)-", word)
        if not hash_type:
            self.cem_type = None
        else:
            self.cem_type = general_dict.get(hash_type.group("type"), "chemical")
        self.type = _type

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if key == 'unit':
                self.unit = value
            elif key == 'value':
                self.value = value
            elif key == 'group' and isinstance(value, list):
                self.group = value
            elif key == '_type':
                self.type = value

    def value_match(self, new_value):
        # print ('value', self.value, 'target', new_value.target, 'group', new_value.group, 'cem_group', self.group)

        if new_value.target:  # Should be revised
            # compare with before_target

            return

        for value in self.value:  # Should be revised
            if not new_value.isindependent(value):

                distance1 = self.distance_with_word(new_value)
                distance2 = self.distance_with_word(value)

                if distance1 < distance2:
                    # Change value
                    value.clear_target()
                else:
                    # print ("ERROR1 : 겹쳐요", value, new_value)
                    return

        num_cluster = len(self.group)
        if num_cluster == 1:
            if new_value.group_overlap:
                # print ("ERROR:overlap matching (value>1)")
                pass

            else:
                for value in new_value.group:
                    value.target = self
                    self.value.append(value)

        elif num_cluster == len(new_value.group):
            for v1, v2 in zip(self.group, new_value.group):
                v2.target = v1
                v1.value.append(v2, )

        elif len(new_value.group) == 1:
            type_dict = {}
            for chem in self.group:
                chem_type = chem.type
                if not chem_type or chem_type in type_dict:
                    # print (f"ERROR:not matching1 (num_chemical:{num_cluster}, num_value:{len(new_value.group)})")
                    return
                else:
                    type_dict[chem_type] = chem

            new_value.target = type_dict
            for chem in self.group:
                chem.value.append(new_value)

        else:
            # print (f"ERROR:not matching2 (num_chemical:{num_cluster}, num_value:{len(new_value.group)})")
            pass

        # new_value.target = self

        return


# In[6]:


class Value(Word):
    ''' Value.word = value
    Value.value : value (ex, around 30)
    Value.unit : unit (ex, m2/g)
    Value.unit_dimension : dimension of unit ("[1.0,-2.0,0.0,0.0,0.0,0.0]")
    Value.prop : property of unit (ex, Surface area)
    Value.prop_type : type of property (Character, Reaction, General, Condition, None)
    self.group : list of class <Value>
    self.group_overlap : <bool> each value of groups are dependent / independent
    self.target : class <Chemical> that matched with value    
    '''

    def __init__(self, value, unit_database, unit=None, prop=None, prop_type=None, group=None, total_group=None):
        self.word = value
        self.value = value
        self.keyword = None
        self.unit_hash = unit
        self.unit_database = unit_database
        self.ABB = None
        self._operation = None

        if not unit:
            self.unit, self.unit_cem, self.unit_dimension = None, None, None
        else:
            self.unit = unit_database[unit]['unit']
            self.unit_cem = unit_database[unit]['unit_cem']
            self.unit_dimension = unit_database.unit_analysis[self.unit]

        self.prop = prop
        self.prop_type = prop_type
        self.target = None

        if isinstance(group, list):
            self.group = group
        else:
            self.group = [self]

        self.total_group = total_group

        self.condition = {}
        num_cluster = len(self.group)

        if num_cluster == 1:
            self.group_overlap = False
        else:
            self.group_overlap = True

    def append_group(self, value):
        if not self.group_overlap:
            self.group_overlap = True
        super().append_group(value)

    def append_total_group(self, value):
        if isinstance(value, list):
            for value_each in value:
                self.append_total_group(value_each)
            return

        elif not isinstance(value, Word):
            raise TypeError(type(value))

        elif value is self:
            return
        else:
            self.total_group.append(value, )

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if key == 'unit_hash':
                if not value or not re.match("-u\d\d\d\d\d\d-", value):
                    self.unit, self.unit_cem = None, None
                    self.unit_hash = value
                else:
                    self.unit_hash = value
                    self.unit = self.unit_database[value]['unit']
                    self.unit_cem = self.unit_database[value]['unit_cem']
                    self.unit_dimension = self.unit_database.unit_analysis[self.unit]

            elif key == 'value':
                self.value = value
            elif key == 'prop_type':
                self.prop_type = value
            elif key == 'prop':
                self.prop = value
            elif key == 'group_overlap':
                if isinstance(value, bool):
                    self.group_overlap = value
            elif key == 'group' and isinstance(value, list):
                self.group = value

                num_cluster = len(self.group)
                if num_cluster == 1:
                    self.group_overlap = False
                else:
                    self.group_overlap = True
            elif key == 'total_group' and isinstance(value, list):
                self.total_group = value

    def __repr__(self):
        return "({}/{}/{})".format(self.value, self.unit, self.prop)

    def __str__(self):
        return "({}/{}/{})".format(self.value, self.unit, self.prop)

    def matching(self, other_value, overlap=False):
        prop = other_value.prop
        other_group = other_value.group

        # Overlap is not allowed and Already existed
        if not overlap and prop in self.condition:
            return

        num_cluster = len(self.group)

        if len(other_group) == 1:
            self.condition[prop] = other_value

        elif len(other_group) == num_cluster:
            for v1, v2 in zip(self.group, other_group):
                v1.condition[prop] = v2
                v1.group_overlap = False

        else:
            self.condition[prop] = "check one more time"

    def isindependent(self, other_value):
        if self.prop != other_value.prop:
            return True

        for prop, value in self.condition.items():
            if other_value.condition.get(prop, value) is not value:
                return True

        return False

    def clear_target(self):
        for value_in_group in self.group:
            TargetOfValue = value_in_group.target
            TargetOfValue.value.remove(value_in_group)
            value_in_group.target = None


# In[34]:


class sent_mapping():
    def __init__(self):
        self.alpha = 0
        self.gamma = 0
        self.index = np.zeros(2, dtype='float16')
        self.trainable = True
        self.trainable_type = None
        self.slice_word = {",": 1, "and": 1, 'or': 1, 'while': 2, 'because': 2, 'as': 1, 'however': 1, 'than': 1,
                           'to': 0.5, 'that': 1,
                           'which': 1}
        self.bracket = 0

    def update(self, word, trainable=None):
        if self.trainable or trainable or True:  # should be revised # Always True for this version

            if word in "([{":
                self.bracket += 1
                # self.alpha += 0.01
            elif word in ")]}":
                self.bracket -= 1
                # self.alpha += 0.01

            elif self.bracket:
                self.alpha += 0.01
                self.index[0] += 0.01

            elif word in self.slice_word:
                self.index[1] += self.alpha * self.slice_word.get(word, 1) + 1
                self.alpha = 0



            else:
                self.alpha += 1
                self.index[0] += 1

        if trainable:
            self.trainable = True
        elif isinstance(trainable, bool):
            self.trainable = False

        return tuple(self.index)

    def clear(self):
        self.alpha, self.gamma = 0, 0
        self.index = np.zeros(2, dtype='int16')

    def set_trainable(self, trainable):
        self.trainable = trainable


# In[35]:


def word_nearest(word_list, target, condition=None, consider_phase=True):
    """ find nearest word from target that satisfy condition    
    word : class <Word> (include <Value>, <Chemical>) or list of class <word>
    target : list of class <Word>
    condtion : function that return bool (True / False)
    
    return : class <Word>
    
    ex) word_target = word_nearest(word, list_of_word, lambda word: isinstance(word, Condition))
    """

    if not condition:
        condition = lambda t: True

    min_distance = 100
    min_word = None

    def word_distance(word1, word2):
        position1 = word1.position
        position2 = word2.position

        distance = [a - b for a, b in zip(position1, position2)]

        return np.sum(np.abs(distance))

    if isinstance(word_list, Word):
        word_list = [word_list]
    elif isinstance(word_list, list):
        # word_list = word_list
        pass
    else:
        print(word_list)
        raise TypeError()

    for word in word_list:
        phase = word.phase
        for word_compare in target:
            if not condition(word_compare):
                continue
            elif consider_phase and phase - word_compare.phase:
                continue

            distance = word_distance(word, word_compare)
            # print (word_compare, distance)
            if min_distance > distance:
                min_distance = distance
                min_word = word_compare
            elif min_distance == distance:
                pass
                # should be revised

    return min_word


# In[36]:


def structurization_sent(sent, database, chemical_type_dict):
    """input : sent, chemical_type_dict
    output : new_sent, unit_dictionary, chemical_list
    """
    new_sent = []
    value_mini = []
    chemical_list = []

    if not chemical_type_dict:
        chemical_type_dict = {}

    unit_database = database.get('unit')

    last_cem = None
    last_value = Value(None, None, unit=False)
    sent_position_counter = sent_mapping()
    unit_dict = {}
    represent_chem = True

    for word in sent:
        if re.match(r"-(c|e|i|s)\d\d\d\d\d\d-|-strange\((.+)\)-", word):
            word_c = Chemical(word, database, _type=chemical_type_dict.get(word, None))
            chemical_list.append(word_c)
            word_c.set_position(sent_position_counter.update(word, False))
            new_sent.append(word_c)

            if last_cem:  # Update chemical_group(Existed)
                last_cem.append_group(word_c)
                group_before = last_cem.group
                word_c.update(group=group_before)
            elif isinstance(represent_chem,
                            Chemical) and word_c.cem_type == 'chemical':  # First chemical and represent_cem exist
                represent_chem = False
            elif represent_chem and word_c.cem_type == 'chemical':  # represent_cem == True
                represent_chem = word_c

            last_cem = word_c

        elif re.match(r"-num\((.+)\)-", word):
            num = Value(word_original(word, **database), unit_database)
            new_sent.append(num)
            num.set_position(sent_position_counter.update(word, False))
            value_mini.append(num)

        elif re.match(r"-u\d\d\d\d\d\d-", word):
            """Plz remove this part! -? fp"""
            # class_name, class_type = unit_mergari(word, sent)
            class_name, class_type = None, None

            group = copy.copy(value_mini)
            total_group = copy.copy(value_mini)
            unit = word

            unit_tag = unit_database[unit]
            unit_dim = unit_database.unit_analysis[unit_tag['unit']]
            Update_list_in_dictionary(unit_dict, unit_tag['unit'], *group)  # should be revised

            if unit_dim == '[0.0/0.0/0.0/0.0/0.0/0.0/0.0]':
                if unit == last_value.unit_hash:
                    same_dimension = True
                else:
                    same_dimension = False

            elif last_value.unit_dimension == unit_dim:
                same_dimension = True
            else:
                same_dimension = False

            if same_dimension:  # Same unit_dimension
                last_value.append_group(group)
                last_value.append_total_group(total_group)
                group = last_value.group
                total_group = last_value.total_group

            elif last_value.total_group:
                last_value.append_total_group(total_group)
                total_group = last_value.total_group

            for value in value_mini:
                value.update(unit_hash=unit, prop=class_name, prop_type=class_type, group=group,
                             total_group=total_group)

            # Condition_dictionary
            sent_position_counter.set_trainable(True)
            last_value = Get(group, -1, Value(None, None, unit=False))
            value_mini.clear()


        elif word in [",", '.', 'vs', 'or', 'and', 'to', 'versus']:
            word_c = Word(word, database)
            word_c.set_position(sent_position_counter.update(word, None))
            new_sent.append(word_c)

        else:  # general words

            word_c = Word(word, database)
            word_c.set_position(sent_position_counter.update(word, True))
            new_sent.append(word_c)

            # check if catalyst or not
            if re.match(r'(?i).*catalysts?$', word):
                last_word = Get(new_sent, -1, Word(None))
                if not last_word:
                    pass
                elif re.match(r"(?i)without", last_word.word):
                    without_catalyst = Chemical('Without catalyst', database, 'catalyst')
                    without_catalyst.set_position(last_word.position)
                    new_sent[-1] = without_catalyst
                    chemical_list.append(without_catalyst)

                elif last_cem:
                    for cem in last_cem.group:
                        chemical_type_dict.update({cem.word: 'catalyst'})
                        if not cem.type:
                            cem.update(_type='catalyst')

            elif word in ['cathode', 'cathodes', 'anode', 'anodes', 'electrode', 'electrodes', 'battery', 'cell',
                          'batteries', 'cells']:
                last_word = Get(new_sent, -1, Word(None))
                electrode = re.match(r"(?P<electrode>cathode|anode|electrode)(s|es|ies)?", word)

                if not electrode:
                    type_electrode = 'battery'
                elif electrode.group('electrode') == 'electrode':
                    type_electrode = 'electrode'
                else:
                    type_electrode = electrode.group('electrode')

                if not last_word:
                    pass

                elif last_cem:
                    for cem in last_cem.group:
                        if type_electrode and cem.word not in chemical_type_dict:
                            chemical_type_dict.update({cem.word: type_electrode})
                            cem.type = type_electrode
                        """elif cem.word in chemical_type_dict:
                            type_of_cem = chemical_type_dict.get(cem.word)
                            if type_of_cem in ['anode', 'cathode']:
                                pass
                            else:
                                chemical_type_dict[cem.word] = 'electrode'"""
                    continue

            value_mini.clear()
            if last_value:
                last_value = Value(None, None, unit=False)
            if last_cem:
                last_cem = None
    return new_sent, unit_dict, chemical_list, represent_chem


# In[37]:


def slice_phase(new_sent):
    slice_word = ['than that of', 'compared to', 'compare to', 'compare with', 'comparison to', 'comparison with',
                  'comparable to',
                  'comparable with', 'whereas', 'greater than', 'higher than', 'lower than',
                  'better than', 'larger than', 'bigger than', 'smaller than', 'as same as', 'upper than', 'close to']
    slice_word_iter = map(lambda t: t.split(), slice_word)
    slice_dict = {word[0]: word for word in slice_word_iter}

    phase = 0
    phase_list = []

    word_iter = None

    for wordclass in new_sent:
        word = wordclass.word
        if word_iter:
            try:
                iterWord = next(word_iter)
            except StopIteration:
                iterWord = None

            if not iterWord:
                phase += 1
                word_iter = None
            elif word != iterWord:
                word_iter = None

        elif word in slice_dict:
            word_iter = slice_dict[word]
            word_iter = iter(word_iter[1:])

        wordclass.phase = phase

    return phase_list


# slice_phase("it is greater than before one , greater than smaller one , whereas it is different, whereas it is word".split())


# In[38]:


def find_property(sent, unit_dict, chemical_list):
    """input : output of structurization_sent
    output : sent, unit_dict, unit_dictionary
    * unit_dictionary : {'Condtion':{}, 'Reaction':{}, 'General':{}, 'Character':{}, 'Condition':{}, None:{}}
    
    """

    unit_dictionary = {'Condtion': {}, 'Reaction': {}, 'General': {}, 'Character': {}, 'Condition': {}, None: {}}

    for unit_name, unit_list in unit_dict.items():
        filter_keyword = get_keyword_from_sent(sent, unit_name)

        if not filter_keyword:  # No keyword
            if unit_name in keyword_dict[None]:
                default_keyword = keyword_dict[None].get(unit_name)

            else:
                Dimension = dimension_analysis(unit_name)
                default_keyword = keyword_dict[None].get(Dimension, (None, None, None))

            for unit_temp in unit_list:
                prop_sub = Check(default_keyword[1], default_keyword[0])
                unit_temp.update(prop=prop_sub, prop_type=default_keyword[2])
                insert_in_unit_dictionary(unit_dictionary, default_keyword[2], prop_sub, unit_temp)
                # print (default_keyword[2], prop_sub, unit_temp)

        else:  # Have keyword
            for unit in unit_list:
                if not unit.prop:
                    match_property(unit, sent, filter_keyword, unit_dictionary)

    return sent, unit_dict, unit_dictionary


def insert_in_unit_dictionary(unit_dictionary, class_type, class_name, *group):
    # if class_name existed, insert. Else, make new list and insert
    """if not class_type:
        return"""
    class_dictionary = unit_dictionary[class_type]

    if class_name not in class_dictionary:
        class_dictionary[class_name] = []

    class_dictionary[class_name].extend(group)


def update_keyword_pack(keyword_list, keyword_mini):
    """Update keyword_mini in keyword_list
    """
    # print (keyword_mini)
    keyword_pack = Get(keyword_mini, -1)

    def update_weight(prop_tuple, weight, pack=keyword_pack):
        if prop_tuple in pack:
            pack[prop_tuple] += weight
        else:
            prop, sub_prop, prop_type = prop_tuple
            weight_before = pack.get((prop, None, prop_type), 0)

            pack[prop_tuple] = weight + weight_before

    for prop, sub_prop, prop_type, weight in keyword_list:
        prop_tuple = (prop, sub_prop, prop_type)

        if not sub_prop:  # sub_prop == None
            for pack in keyword_mini:
                if not pack and pack is not keyword_pack:  # pack is empty and it is not last_term
                    continue

                for other_prop in pack:
                    if other_prop[0] == prop and other_prop[1]:  # Update before keyword (sub_prop != None)
                        update_weight(other_prop, weight, pack)

        update_weight(prop_tuple, weight, keyword_pack)

    # print ('ahah', keyword_list, keyword_mini)

    return keyword_mini


def get_keyword_from_sent(sent, unit_name):
    """input : sent, unit_name
    output : filter_keyword
    """
    unit_dimension = dimension_analysis(unit_name)

    keyword_with_prop = {}
    keyword_mini = [{}]

    for word in sent:

        if word.keyword and (unit_name in word.keyword or unit_dimension in word.keyword):
            """keyword_pack = Get(keyword_mini, -1)
            keyword_list = word.keyword.get(unit_name)
            
            update_keyword_pack(keyword_list, keyword_pack)"""

            keyword_list1 = word.keyword.get(unit_name)
            keyword_list2 = word.keyword.get(unit_dimension)

            # print (keyword_list1, keyword_list2)
            if keyword_list1:
                update_keyword_pack(keyword_list1, keyword_mini)

            if keyword_list2:
                update_keyword_pack(keyword_list2, keyword_mini)

            keyword_with_prop[word] = keyword_mini

        elif str(word) in [",", '.', 'vs', 'or', 'and', 'to', 'versus']:
            keyword_mini.append({})

        elif str(word) in ["(", ")", 'of', 'for']:
            pass

        elif keyword_mini:
            keyword_mini = [{}]

        else:
            activation = False

    # print ('kwp', keyword_with_prop)
    filter_keyword = {}

    for word, keyword_mini in keyword_with_prop.items():
        keyword_mini_revise = list(filter(lambda keyword: keyword, keyword_mini))

        # print (word, keyword_mini_revise)
        best_keyword2 = list(map(lambda keyword_pack: sorted(keyword_pack.items(), reverse=True,
                                                             key=lambda t: t[1])[0],
                                 keyword_mini_revise))

        best_keyword = [prop[0] for prop in best_keyword2 if prop[1] >= 1]

        # print (best_keyword, best_keyword2)
        if best_keyword:
            filter_keyword[word] = best_keyword

    return filter_keyword


def match_property(unit, sent, filter_keyword, unit_dictionary):
    matched_word = word_nearest(unit, filter_keyword, consider_phase=False)
    # print (unit, matched_word)

    matched_property = filter_keyword.get(matched_word, [(None, None, None)])

    num_property = len(matched_property)
    unit_group = unit.group
    activation = False

    if num_property == 1:
        matched_property_iter = repeat(matched_property[0], len(unit.group))
        group_overlap_TF = None

    elif num_property == len(unit.group):
        matched_property_iter = matched_property
        group_overlap_TF = False

    elif num_property == len(unit.total_group):
        activation = True
        unit_group = unit.total_group
        matched_property_iter = matched_property
        group_overlap_TF = False

    else:
        text = f"property matching ERROR, {num_property}, {len(unit.group)}, {unit}, {matched_property}"
        warnings.warn(text)
        return

    for property_temp, unit_temp in zip(matched_property_iter, unit_group):
        if activation and unit_temp.unit_dimension != unit.unit_dimension:
            continue

        prop_sub = Check(property_temp[1], property_temp[0])
        unit_temp.update(prop=prop_sub, prop_type=property_temp[2], group_overlap=group_overlap_TF)
        insert_in_unit_dictionary(unit_dictionary, property_temp[2], prop_sub, unit_temp)

    return matched_property


# In[48]:


def matching_algorithm(sent, database, chemical_type_dict, before_represent_chem=False):
    """input : sent
    output : revised_sent, unit_dictionary"""

    revised_sent, unit_dict, chemical_list, next_represent_chem = structurization_sent(sent, database,
                                                                                       chemical_type_dict)
    slice_phase(revised_sent)

    _, _, unit_dictionary = find_property(revised_sent, unit_dict, chemical_list)

    condition_dictionary = unit_dictionary['Condition']
    character_dictionary = unit_dictionary['Character']
    reaction_dictionary = unit_dictionary['Reaction']
    general_dictionary = unit_dictionary['General']

    # total_values = reduce(lambda x, y : x + y, chain(character_dictionary.values(), reaction_dictionary.values()), [])
    character_value = list(chain.from_iterable(character_dictionary.values()))
    reaction_value = list(chain.from_iterable(reaction_dictionary.values()))
    general_value = list(chain.from_iterable(general_dictionary.values()))

    for class_name, conditions in condition_dictionary.items():
        for value in character_value + reaction_value:
            if class_name in value.condition:
                continue

            matched_condition = word_nearest(value.group, conditions, consider_phase=False)
            if not isinstance(matched_condition, Value):
                continue

            for grouped_value in value.group:
                if not grouped_value:
                    continue
                grouped_value.matching(matched_condition, overlap=False)

    for value in general_value:
        matched_chemical = word_nearest(value.group, chemical_list,
                                        lambda t: isinstance(t, Chemical))  # Possible all things
        if not matched_chemical:
            continue

        distance = value.distance_with_word(matched_chemical)
        if distance < 6:
            matched_chemical.value_match(value)

    for value in character_value:
        # Remove cased
        if value.target:
            continue

        matched_chemical = word_nearest(value.group, chemical_list,
                                        lambda t: isinstance(t, Chemical) and t.cem_type == 'chemical')

        if not isinstance(matched_chemical, Chemical):  # Matching with before_chemical
            if value.phase:  # phase > 0
                continue
            if isinstance(before_represent_chem, Chemical):
                matched_chemical = before_represent_chem
            elif not before_represent_chem:
                continue
            else:
                raise TypeError("before_represent_chem should be class <Chemical> or False")

        for grouped_value in value.group:
            if not grouped_value:
                continue

            matched_chemical.value_match(value)

    for value in reaction_value:  # Should be revised
        matched_chemical = word_nearest(value, chemical_list,
                                        lambda t: isinstance(t, Chemical) and t.type == 'catalyst')
        # print (matched_chemical)

        if isinstance(matched_chemical, Chemical):
            matched_chemical.value_match(value)

    return revised_sent, unit_dictionary, next_represent_chem
