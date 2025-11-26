#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VST Plugin Scanner v7.1 - Ultimate Edition (Safer Manufacturer Detection)
Честный детект производителей с минимальным количеством ложных срабатываний.
"""

import json
import os
import sys
import csv
import argparse
import struct
import winreg
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Iterable, Set
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict

try:
    import pefile
    PEFILE_AVAILABLE = True
except ImportError:
    PEFILE_AVAILABLE = False
    print("⚠️ Библиотека pefile не установлена. Установите: pip install pefile\n")

# ==============================================================================
# РАСШИРЕННАЯ БАЗА ДАННЫХ ПРОИЗВОДИТЕЛЕЙ
# ==============================================================================

# Прямое сопоставление имен плагинов с производителями (САМЫЙ НАДЕЖНЫЙ МЕТОД)
# ВАЖНО: здесь ключи — ИМЕНА/ФРАГМЕНТЫ ИМЕН ПЛАГИНОВ, а не производителей.
PLUGIN_NAME_TO_MANUFACTURER: Dict[str, str] = {
    # Antares
    'auto-tune': 'Antares', 'autotune': 'Antares', 'efx': 'Antares',
    'throat': 'Antares', 'harmony engine': 'Antares', 'mic mod': 'Antares',
    'avox': 'Antares', 'choir': 'Antares', 'articulator': 'Antares',
    'aspire': 'Antares', 'duo': 'Antares', 'mutator': 'Antares',
    'warm': 'Antares', 'punch': 'Antares', 'sybil': 'Antares',
    'auto-tune vocal eq': 'Antares', 'vocal eq': 'Antares',

    # iZotope
    'ozone': 'iZotope', 'neutron': 'iZotope', 'nectar': 'iZotope',
    'rx': 'iZotope', 'neoverb': 'iZotope', 'trash': 'iZotope',
    'relay': 'iZotope', 'insight': 'iZotope', 'vocal synth': 'iZotope',
    'vocalsynth': 'iZotope', 'stutter edit': 'iZotope', 'iris': 'iZotope',
    'breaktweaker': 'iZotope', 'ddly': 'iZotope', 'mobius': 'iZotope',
    'vinyl': 'iZotope', 'spectral shaper': 'iZotope', 'dialogue match': 'iZotope',
    'audiolens': 'iZotope', 'tonal balance': 'iZotope', 'master rebalance': 'iZotope',
    'lowender': 'iZotope', 'stratus': 'iZotope', 'symphony': 'iZotope',

    # FabFilter
    'pro-q': 'FabFilter', 'pro-c': 'FabFilter', 'pro-l': 'FabFilter',
    'pro-r': 'FabFilter', 'pro-mb': 'FabFilter', 'pro-ds': 'FabFilter',
    'pro-g': 'FabFilter', 'saturn': 'FabFilter', 'timeless': 'FabFilter',
    'volcano': 'FabFilter', 'twin': 'FabFilter', 'micro': 'FabFilter',
    'simplon': 'FabFilter', 'one': 'FabFilter',

    # Waves
    'abbey road': 'Waves', 'api': 'Waves', 'ssl': 'Waves', 'cla': 'Waves',
    'h-delay': 'Waves', 'h-comp': 'Waves', 'h-reverb': 'Waves',
    'l1': 'Waves', 'l2': 'Waves', 'l3': 'Waves', 'linear phase': 'Waves',
    'maxbass': 'Waves', 'maxxbass': 'Waves', 'manny marroquin': 'Waves',
    'c1': 'Waves', 'c4': 'Waves', 'c6': 'Waves', 'dbx': 'Waves',
    'deesser': 'Waves', 'doubler': 'Waves', 'enigma': 'Waves',
    'gtr': 'Waves', 'kramer': 'Waves', 'metaflanger': 'Waves',
    'mondomod': 'Waves', 'morphoder': 'Waves', 'nx': 'Waves',
    'prs': 'Waves', 'puigchild': 'Waves', 'puigtec': 'Waves',
    'q10': 'Waves', 'r-bass': 'Waves', 'rbass': 'Waves',
    'rvox': 'Waves', 's1': 'Waves', 'scheps': 'Waves',
    'sibilance': 'Waves', 'supertap': 'Waves', 'trans-x': 'Waves',
    'trueverb': 'Waves', 'ultramaximizer': 'Waves',
    'vitamin': 'Waves', 'vocal rider': 'Waves', 'vocalrider': 'Waves',
    'waveslink': 'Waves', 'z-noise': 'Waves', 'torque': 'Waves',
    'brauer': 'Waves', 'cobalt': 'Waves', 'clarity': 'Waves',
    'cosmos': 'Waves', 'magma': 'Waves', 'smack': 'Waves',
    'platinum': 'Waves', 'diamond': 'Waves', 'gold': 'Waves',
    'renaissance': 'Waves', 'v-series': 'Waves',
    'waves tune': 'Waves', 'wavestune': 'Waves',

    # Valhalla
    'valhalla': 'Valhalla DSP', 'valhallaroom': 'Valhalla DSP',
    'valhallaplate': 'Valhalla DSP', 'valhallavintage': 'Valhalla DSP',
    'valhallashimmer': 'Valhalla DSP', 'valhalladelay': 'Valhalla DSP',
    'valhallasupermassive': 'Valhalla DSP', 'valhallafreqecho': 'Valhalla DSP',
    'valhallaspacemods': 'Valhalla DSP', 'valhallaubermod': 'Valhalla DSP',

    # Soundtoys
    'decapitator': 'Soundtoys', 'echoboy': 'Soundtoys', 'crystallizer': 'Soundtoys',
    'microshift': 'Soundtoys', 'panman': 'Soundtoys', 'tremolator': 'Soundtoys',
    'filterfreak': 'Soundtoys', 'phasemistress': 'Soundtoys', 'primaltap': 'Soundtoys',
    'radiator': 'Soundtoys', 'devil-loc': 'Soundtoys', 'devloc': 'Soundtoys',
    'little plate': 'Soundtoys', 'littleplate': 'Soundtoys', 'sie-q': 'Soundtoys',
    'alterboy': 'Soundtoys', 'effect rack': 'Soundtoys',

    # Plugin Alliance / Brainworx
    'bx_': 'Plugin Alliance', 'brainworx': 'Plugin Alliance',
    'elysia': 'Plugin Alliance', 'lindell': 'Plugin Alliance',
    'millennia': 'Plugin Alliance', 'neold': 'Plugin Alliance',
    'shadow hills': 'Plugin Alliance', 'spl': 'Plugin Alliance',
    'unfiltered audio': 'Plugin Alliance', 'megasingle': 'Plugin Alliance',

    # Universal Audio
    'uad': 'Universal Audio', 'neve': 'Universal Audio', 'studer': 'Universal Audio',
    'lexicon': 'Universal Audio', 'emt': 'Universal Audio', 'pultec': 'Universal Audio',
    'fairchild': 'Universal Audio', 'la-2a': 'Universal Audio', '1176': 'Universal Audio',
    'oxide': 'Universal Audio', 'capitol chambers': 'Universal Audio',
    'galaxy tape': 'Universal Audio', 'ocean way': 'Universal Audio',
    'spartan': 'Universal Audio',

    # Native Instruments
    'kontakt': 'Native Instruments', 'massive': 'Native Instruments',
    'reaktor': 'Native Instruments', 'guitar rig': 'Native Instruments',
    'battery': 'Native Instruments', 'fm8': 'Native Instruments',
    'absynth': 'Native Instruments', 'maschine': 'Native Instruments',
    'razor': 'Native Instruments', 'monark': 'Native Instruments',
    'replika': 'Native Instruments', 'molekular': 'Native Instruments',
    'driver': 'Native Instruments', 'supercharger': 'Native Instruments',
    'solid': 'Native Instruments', 'transient master': 'Native Instruments',
    'komplete': 'Native Instruments', 'kinetic': 'Native Instruments',
    'session guitarist': 'Native Instruments', 'session horns': 'Native Instruments',
    'session strings': 'Native Instruments', 'symphony series': 'Native Instruments',

    # Arturia
    'analog lab': 'Arturia', 'pigments': 'Arturia', 'mini v': 'Arturia',
    'prophet': 'Arturia', 'jupiter': 'Arturia', 'cs-80': 'Arturia',
    'matrix-12': 'Arturia', 'dx7': 'Arturia', 'synclavier': 'Arturia',
    'cmi': 'Arturia', 'buchla': 'Arturia', 'mellotron': 'Arturia',
    'piano v': 'Arturia', 'stage-73': 'Arturia', 'wurli': 'Arturia',
    'farfisa': 'Arturia', 'vox continental': 'Arturia', 'b-3': 'Arturia',
    'comp vca': 'Arturia', 'comp tube': 'Arturia', 'comp fet': 'Arturia',
    'pre 1973': 'Arturia', 'pre trida': 'Arturia', 'delay tape': 'Arturia',
    'reverb plate': 'Arturia', 'rev intensity': 'Arturia', 'bus force': 'Arturia',
    'efx fragments': 'Arturia', 'augmented': 'Arturia',

    # Softube
    'console 1': 'Softube', 'harmonics': 'Softube', 'modular': 'Softube',
    'tsar': 'Softube', 'amp room': 'Softube', 'model 72': 'Softube',
    'weiss': 'Softube', 'summit audio': 'Softube', 'fix': 'Softube',
    'saturation knob': 'Softube', 'heartbeat': 'Softube', 'parallels': 'Softube',

    # Slate Digital
    'virtual tape': 'Slate Digital', 'virtual console': 'Slate Digital',
    'virtual mix rack': 'Slate Digital', 'vmr': 'Slate Digital',
    'vms': 'Slate Digital', 'vbc': 'Slate Digital', 'vcc': 'Slate Digital',
    'fg-x': 'Slate Digital', 'fg-mu': 'Slate Digital', 'fg-116': 'Slate Digital',
    'fg-401': 'Slate Digital', 'fg-n': 'Slate Digital', 'fg-s': 'Slate Digital',
    'fresh air': 'Slate Digital', 'revival': 'Slate Digital',
    'eiosis': 'Slate Digital', 'airtex': 'Slate Digital',
    'infinity eq': 'Slate Digital', 'lustrous plates': 'Slate Digital',
    'verbsuite': 'Slate Digital', 'metaverb': 'Slate Digital',

    # Eventide
    'h3000': 'Eventide', 'h910': 'Eventide', 'h949': 'Eventide',
    'instant phaser': 'Eventide', 'instant flanger': 'Eventide',
    'omnipressor': 'Eventide', 'ultratap': 'Eventide', 'blackhole': 'Eventide',
    'mangledverb': 'Eventide', 'micropitch': 'Eventide', 'quadravox': 'Eventide',
    'rotary mod': 'Eventide', 'shimmerverb': 'Eventide', 'sp2016': 'Eventide',
    'physion': 'Eventide', 'fission': 'Eventide', 'spliteq': 'Eventide',
    'tverb': 'Eventide', 'undulator': 'Eventide', 'crystals': 'Eventide',

    # Celemony
    'melodyne': 'Celemony',

    # Sonnox
    'oxford': 'Sonnox', 'inflator': 'Sonnox', 'supressor': 'Sonnox',
    'envolution': 'Sonnox', 'claro': 'Sonnox', 'voxdoubler': 'Sonnox',

    # Tokyo Dawn Records
    'tdr': 'Tokyo Dawn Records', 'slick eq': 'Tokyo Dawn Records',
    'nova': 'Tokyo Dawn Records', 'kotelnikov': 'Tokyo Dawn Records',
    'limiter 6': 'Tokyo Dawn Records', 'molotok': 'Tokyo Dawn Records',
    'proximity': 'Tokyo Dawn Records',

    # LiquidSonics
    'seventh heaven': 'LiquidSonics', 'reverberate': 'LiquidSonics',
    'cinematic rooms': 'LiquidSonics', 'tai chi': 'LiquidSonics',
    'lustrous plates': 'LiquidSonics', 'illusion': 'LiquidSonics',

    # Acustica Audio
    'acqua': 'Acustica Audio', 'cream': 'Acustica Audio', 'sand': 'Acustica Audio',
    'navy': 'Acustica Audio', 'fire': 'Acustica Audio', 'gold': 'Acustica Audio',
    'coral': 'Acustica Audio', 'jade': 'Acustica Audio', 'taupe': 'Acustica Audio',
    'tan': 'Acustica Audio', 'purple': 'Acustica Audio', 'magenta': 'Acustica Audio',
    'crimson': 'Acustica Audio', 'nebula': 'Acustica Audio', 'titanium': 'Acustica Audio',
    'amethyst': 'Acustica Audio', 'amber': 'Acustica Audio', 'rose': 'Acustica Audio',
    'coffee': 'Acustica Audio', 'diamond': 'Acustica Audio', 'ultramarine': 'Acustica Audio',
    'lava': 'Acustica Audio',

    # IK Multimedia
    'amplitube': 'IK Multimedia', 't-racks': 'IK Multimedia', 'tracks': 'IK Multimedia',
    'modo bass': 'IK Multimedia', 'modo drum': 'IK Multimedia', 'miroslav': 'IK Multimedia',
    'sampletank': 'IK Multimedia', 'syntronik': 'IK Multimedia', 'lurssen': 'IK Multimedia',
    'master eq': 'IK Multimedia', 'tape echo': 'IK Multimedia',

    # Xfer Records
    'serum': 'Xfer Records', 'cthulhu': 'Xfer Records', 'ott': 'Xfer Records',
    'lfotool': 'Xfer Records', 'nerve': 'Xfer Records',

    # Spectrasonics
    'omnisphere': 'Spectrasonics', 'keyscape': 'Spectrasonics',
    'trilian': 'Spectrasonics', 'stylus': 'Spectrasonics',

    # u-he
    'diva': 'u-he', 'hive': 'u-he', 'zebra': 'u-he', 'repro': 'u-he',
    'bazille': 'u-he', 'ace': 'u-he', 'presswerk': 'u-he', 'satin': 'u-he',
    'colour copy': 'u-he', 'twangstrom': 'u-he', 'podolski': 'u-he',
    'tyrell': 'u-he', 'triple cheese': 'u-he', 'protoverb': 'u-he',
    'filterscape': 'u-he', 'uhbik': 'u-he',

    # Kilohearts
    'phase plant': 'Kilohearts', 'snap heap': 'Kilohearts',
    'multipass': 'Kilohearts', 'disperser': 'Kilohearts',
    'faturator': 'Kilohearts', 'bitcrush': 'Kilohearts',
    'carve eq': 'Kilohearts', 'transient shaper': 'Kilohearts',

    # Cableguys
    'shaperbox': 'Cableguys', 'volumeshaper': 'Cableguys',
    'filtershaper': 'Cableguys', 'timeshaper': 'Cableguys',
    'panshaper': 'Cableguys', 'wideshaper': 'Cableguys',
    'noiseshaper': 'Cableguys', 'crushershaper': 'Cableguys',
    'halftime': 'Cableguys', 'curve': 'Cableguys',

    # Polyverse
    'manipulator': 'Polyverse', 'infected': 'Polyverse',
    'gatekeeper': 'Polyverse', 'comet': 'Polyverse',
    'wider': 'Polyverse', 'filterverse': 'Polyverse',

    # Goodhertz
    'vulf compressor': 'Goodhertz', 'lossy': 'Goodhertz', 'tupe': 'Goodhertz',
    'wow control': 'Goodhertz', 'panpot': 'Goodhertz', 'tone control': 'Goodhertz',
    'faraday limiter': 'Goodhertz', 'lohi': 'Goodhertz', 'midside': 'Goodhertz',
    'trem control': 'Goodhertz', 'canopener': 'Goodhertz', '3d': 'Goodhertz',

    # Baby Audio
    'comeback kid': 'Baby Audio', 'crystalline': 'Baby Audio', 'ba-1': 'Baby Audio',
    'super vhs': 'Baby Audio', 'parallel aggressor': 'Baby Audio', 'taip': 'Baby Audio',
    'smooth operator': 'Baby Audio', 'transit': 'Baby Audio', 'spaced out': 'Baby Audio',

    # Oeksound
    'soothe': 'Oeksound', 'spiff': 'Oeksound', 'bloom': 'Oeksound',

    # PSPaudioware
    'psp': 'PSPaudioware', 'vintage warmer': 'PSPaudioware',
    'xenon': 'PSPaudioware', 'infinistrip': 'PSPaudioware',

    # DMGAudio
    'compassion': 'DMGAudio', 'equilibrium': 'DMGAudio', 'essence': 'DMGAudio',
    'expurgate': 'DMGAudio', 'dualism': 'DMGAudio', 'limitless': 'DMGAudio',
    'multiplicity': 'DMGAudio', 'pitchfunk': 'DMGAudio', 'trackcomp': 'DMGAudio',
    'trackds': 'DMGAudio', 'tracklimit': 'DMGAudio', 'trackcontrol': 'DMGAudio',
    'trackmeter': 'DMGAudio',

    # Audio Damage
    'dubstation': 'Audio Damage', 'eos': 'Audio Damage', 'fuzz+': 'Audio Damage',
    'grind': 'Audio Damage', 'liquid': 'Audio Damage', 'phosphor': 'Audio Damage',
    'ratshack reverb': 'Audio Damage', 'replicant': 'Audio Damage',
    'rough rider': 'Audio Damage', 'sequencer 1': 'Audio Damage',

    # McDSP
    'compressor bank': 'McDSP', 'filterbank': 'McDSP', 'ml4000': 'McDSP',
    'mc2000': 'McDSP', 'futzbox': 'McDSP', 'analog channel': 'McDSP',

    # Acon Digital
    'acoustica': 'Acon Digital', 'declick': 'Acon Digital', 'declipper': 'Acon Digital',
    'deconvolver': 'Acon Digital', 'dehum': 'Acon Digital', 'denoise': 'Acon Digital',
    'deverb': 'Acon Digital', 'equalize': 'Acon Digital', 'extract': 'Acon Digital',
    'limit': 'Acon Digital', 'master': 'Acon Digital', 'restoration suite': 'Acon Digital',
    'verberate': 'Acon Digital', 'vitalize': 'Acon Digital', 'multiply': 'Acon Digital',

    # 2CAudio
    'aether': '2CAudio', 'breeze': '2CAudio', 'b2': '2CAudio',
    'kaleidoscope': '2CAudio', 'precedence': '2CAudio',

    # Overloud
    'th-u': 'Overloud', 'gem': 'Overloud', 'mark studio': 'Overloud',
    'springage': 'Overloud', 'breverb': 'Overloud', 'rematrix': 'Overloud',

    # Blue Cat Audio
    'blue cat': 'Blue Cat Audio', 'patchwork': 'Blue Cat Audio',
    'mb-7': 'Blue Cat Audio', 'destructor': 'Blue Cat Audio',
    'axiom': 'Blue Cat Audio', 'late replies': 'Blue Cat Audio',

    # Steinberg
    'halion': 'Steinberg', 'groove agent': 'Steinberg', 'padshop': 'Steinberg',
    'retrologue': 'Steinberg', 'backbone': 'Steinberg', 'cubasis': 'Steinberg',
    'frequency': 'Steinberg', 'hypnotic': 'Steinberg', 'mystic': 'Steinberg',
    'prologue': 'Steinberg', 'spector': 'Steinberg', 'amped': 'Steinberg',

    # SSL
    'ssl native': 'SSL', 'bus compressor': 'SSL', 'channel strip': 'SSL',
    'x-eq': 'SSL', 'x-comp': 'SSL', 'x-orcism': 'SSL', 'drumstrip': 'SSL',
    'vocstrip': 'SSL', 'channelstrip': 'SSL', 'flexpander': 'SSL',
    'vocalstrip': 'SSL', 'fusion': 'SSL',

    # Zynaptiq
    'adaptiverb': 'Zynaptiq', 'intensity': 'Zynaptiq', 'morph': 'Zynaptiq',
    'pitchmap': 'Zynaptiq', 'unveil': 'Zynaptiq', 'unfilter': 'Zynaptiq',
    'unmix': 'Zynaptiq', 'wormhole': 'Zynaptiq',

    # Newfangled Audio
    'elevate': 'Newfangled Audio', 'saturate': 'Newfangled Audio',
    'pendulate': 'Newfangled Audio', 'generate': 'Newfangled Audio',

    # Accusonus
    'beatformer': 'Accusonus', 'drumatom': 'Accusonus', 'era bundle': 'Accusonus',
    'regroover': 'Accusonus', 'rhythmiq': 'Accusonus',

    # iZotope RX modules
    'voice de-noise': 'iZotope', 'de-hum': 'iZotope', 'de-clip': 'iZotope',
    'de-click': 'iZotope', 'de-crackle': 'iZotope', 'de-reverb': 'iZotope',
    'spectral de-noise': 'iZotope', 'dialogue isolate': 'iZotope',
    'music rebalance': 'iZotope', 'breath control': 'iZotope',
    'de-rustle': 'iZotope', 'de-plosive': 'iZotope', 'de-bleed': 'iZotope',
    'de-ess': 'iZotope', 'ambience match': 'iZotope', 'loudness': 'iZotope',

    # Leapwing
    'centerone': 'Leapwing Audio', 'dynone': 'Leapwing Audio',
    'rootone': 'Leapwing Audio', 'stageone': 'Leapwing Audio',
    'al schmitt': 'Leapwing Audio',

    # Vertigo Sound
    'vsc-2': 'Vertigo Sound', 'vsc-3': 'Vertigo Sound',
    'vsm-3': 'Vertigo Sound', 'vse-2': 'Vertigo Sound',

    # Tone Empire
    'reelight pro': 'Tone Empire', 'goliath': 'Tone Empire',
    'loc-ness': 'Tone Empire', 'model 5000': 'Tone Empire',
    'attreides': 'Tone Empire', 'firechild': 'Tone Empire',
    'neural q': 'Tone Empire', 'apt-2a': 'Tone Empire',

    # Black Rooster Audio
    'vpre-73': 'Black Rooster Audio', 'ro-gold': 'Black Rooster Audio',
    'magnetite': 'Black Rooster Audio', 'vla-2a': 'Black Rooster Audio',
    'vla-3a': 'Black Rooster Audio', 'vhl-3c': 'Black Rooster Audio',
    'vcomp-99': 'Black Rooster Audio', 'veq-1a': 'Black Rooster Audio',

    # UJAM
    'finisher': 'UJAM', 'beatmaker': 'UJAM', 'virtual guitarist': 'UJAM',
    'virtual bassist': 'UJAM', 'virtual drummer': 'UJAM', 'usynth': 'UJAM',

    # Neural DSP
    'archetype': 'Neural DSP', 'parallax': 'Neural DSP', 'quad cortex': 'Neural DSP',
    'plini': 'Neural DSP', 'nolly': 'Neural DSP', 'gojira': 'Neural DSP',
    'cory wong': 'Neural DSP', 'tim henson': 'Neural DSP', 'rabea': 'Neural DSP',

    # Dear Reality
    'exoverb': 'Dear Reality', 'dearvr': 'Dear Reality',

    # Devious Machines
    'duck': 'Devious Machines', 'infiltrator': 'Devious Machines',
    'pitch monster': 'Devious Machines', 'texture': 'Devious Machines',

    # WA Production
    'midiq': 'W.A. Production', 'instachord': 'W.A. Production',
    'pumper': 'W.A. Production', 'mutant delay': 'W.A. Production',
    'imprint': 'W.A. Production', 'outlaw': 'W.A. Production',

    # Unison Audio
    'midi chord pack': 'Unison Audio', 'midi wizard': 'Unison Audio',

    # AIR Music Technology
    'hybrid': 'AIR Music Technology', 'loom': 'AIR Music Technology',
    'vacuum': 'AIR Music Technology', 'velvet': 'AIR Music Technology',
    'strike': 'AIR Music Technology', 'structure': 'AIR Music Technology',
    'xpand': 'AIR Music Technology', 'mini grand': 'AIR Music Technology',
    'boom': 'AIR Music Technology', 'db-33': 'AIR Music Technology',

    # Rob Papen
    'blade': 'Rob Papen', 'blue': 'Rob Papen', 'predator': 'Rob Papen',
    'punch': 'Rob Papen', 'raw': 'Rob Papen', 'subboombass': 'Rob Papen',
    'vecto': 'Rob Papen', 'go2': 'Rob Papen', 'rp-verb': 'Rob Papen',
    'rp-delay': 'Rob Papen', 'rp-distort': 'Rob Papen',

    # Reveal Sound
    'spire': 'Reveal Sound',

    # Lennar Digital
    'sylenth1': 'LennarDigital', 'sylenth': 'LennarDigital',

    # Synapse Audio
    'dune': 'Synapse Audio', 'obsession': 'Synapse Audio',
    'the legend': 'Synapse Audio', 'rack extensions': 'Synapse Audio',

    # Waldorf
    'largo': 'Waldorf', 'nave': 'Waldorf', 'quantum': 'Waldorf',
    'ppg wave': 'Waldorf', 'attack': 'Waldorf', 'd-pole': 'Waldorf',

    # TAL
    'tal-': 'TAL-Togu Audio Line', 'noisemaker': 'TAL-Togu Audio Line',
    'bassline': 'TAL-Togu Audio Line', 'sampler': 'TAL-Togu Audio Line',
    'elek7ro': 'TAL-Togu Audio Line', 'dac': 'TAL-Togu Audio Line',
    'reverb': 'TAL-Togu Audio Line', 'vocoder': 'TAL-Togu Audio Line',

    # Melda Production
    'mautopitch': 'MeldaProduction', 'mautodynamic': 'MeldaProduction',
    'mequalizer': 'MeldaProduction', 'mcompressor': 'MeldaProduction',
    'mlimiter': 'MeldaProduction', 'mreverb': 'MeldaProduction',
    'mflanger': 'MeldaProduction', 'mfreeshaper': 'MeldaProduction',

    # Analog Obsession (free plugins)
    'rare': 'Analog Obsession', 'fetish': 'Analog Obsession',
    'tbar': 'Analog Obsession', 'dist': 'Analog Obsession',
    'merica': 'Analog Obsession', 'britpre': 'Analog Obsession',
    'lala': 'Analog Obsession', 'britchannel': 'Analog Obsession',
    'buster': 'Analog Obsession', 'channev': 'Analog Obsession',

    # Voxengo
    'span': 'Voxengo', 'elephant': 'Voxengo', 'pristine': 'Voxengo',
    'deft compressor': 'Voxengo', 'gliss eq': 'Voxengo', 'warmifier': 'Voxengo',
    'teote': 'Voxengo', 'tube amp': 'Voxengo', 'marvel gem': 'Voxengo',
    'boogex': 'Voxengo', 'crunchessor': 'Voxengo', 'marquis': 'Voxengo',
    'sound delay': 'Voxengo', 'correlometer': 'Voxengo', 'overtone gem': 'Voxengo',

    # Audiority
    'polaris': 'Audiority', 'grainspace': 'Audiority',
    'echoes': 'Audiority', 'l12x': 'Audiority', 'the abuser': 'Audiority',
    'box bass': 'Audiority', 'solidus': 'Audiority',

    # Audio Assault
    'amp modeler': 'Audio Assault', 'demongate': 'Audio Assault',
    'axxelerator': 'Audio Assault', 'defacer': 'Audio Assault',
    'headcrusher': 'Audio Assault', 'hellbeast': 'Audio Assault',
    'sigma': 'Audio Assault', 'transient+': 'Audio Assault',

    # Chow DSP
    'chow': 'Chow DSP', 'chowphatty': 'Chow DSP',
    'chow tape model': 'Chow DSP', 'chow centaur': 'Chow DSP',

    # Output
    'thermal': 'Output', 'portal': 'Output', 'exhale': 'Output',
    'signal': 'Output', 'movement': 'Output', 'arcade': 'Output',
    'substance': 'Output', 'analog strings': 'Output', 'analog brass': 'Output',

    # Infected Mushroom
    'i wish': 'Infected Mushroom', 'gatekeeper': 'Infected Mushroom',
    'pusher': 'Infected Mushroom', 'wider': 'Infected Mushroom',
    'bomber': 'Infected Mushroom',

    # D16 Group
    'lush': 'D16 Group', 'decimort': 'D16 Group', 'devastor': 'D16 Group',
    'drumazon': 'D16 Group', 'fazortan': 'D16 Group', 'frontier': 'D16 Group',
    'godfazer': 'D16 Group', 'nithonat': 'D16 Group', 'punchbox': 'D16 Group',
    'redoptor': 'D16 Group', 'repeater': 'D16 Group', 'sigmund': 'D16 Group',
    'syntorus': 'D16 Group', 'toraverb': 'D16 Group', 'phoscyon': 'D16 Group',

    # Glitchmachines
    'cataract': 'Glitchmachines', 'convex': 'Glitchmachines',
    'cryogen': 'Glitchmachines', 'fracture': 'Glitchmachines',
    'hysteresis': 'Glitchmachines', 'palindrome': 'Glitchmachines',
    'quadrant': 'Glitchmachines', 'scope': 'Glitchmachines',

    # Aegean Music
    'spirit eq': 'Aegean Music', 'pitchproof': 'Aegean Music',
    'doppler': 'Aegean Music', 'devil spring': 'Aegean Music',

    # Auburn Sounds
    'graillon': 'Auburn Sounds', 'couture': 'Auburn Sounds',

    # TBProAudio (убраны супер-опасные короткие ключи 'la', 'cs')
    'dseq': 'TBProAudio', 'dpmeq': 'TBProAudio', 'isol8': 'TBProAudio',
    'gseq': 'TBProAudio', 'dseq3': 'TBProAudio',

    # Boz Digital Labs
    'mongoose': 'Boz Digital Labs', 'the wall': 'Boz Digital Labs',
    'panther': 'Boz Digital Labs', 'bark of dog': 'Boz Digital Labs',
    '+10db': 'Boz Digital Labs', 'manic compressor': 'Boz Digital Labs',
    'imperial delay': 'Boz Digital Labs', 'hoser': 'Boz Digital Labs',

    # SIR Audio Tools
    'standard clip': 'SIR Audio Tools', 'standard channel': 'SIR Audio Tools',

    # Fuse Audio Labs
    'rs-w2395c': 'Fuse Audio Labs', 'vce-118': 'Fuse Audio Labs',
    'vpre-31a': 'Fuse Audio Labs', 'vqp-150': 'Fuse Audio Labs',

    # Klanghelm
    'dc8c': 'Klanghelm', 'dc1a': 'Klanghelm', 'mjuc': 'Klanghelm',
    'sdrr': 'Klanghelm', 'ivgi': 'Klanghelm', 'vumt': 'Klanghelm',

    # Cherry Audio
    'voltage modular': 'Cherry Audio', 'memorymode': 'Cherry Audio',
    'ps-20': 'Cherry Audio', 'eight voice': 'Cherry Audio',
    'dco-106': 'Cherry Audio', 'ca2600': 'Cherry Audio',
    'mercury': 'Cherry Audio', 'dreamsynth': 'Cherry Audio',
    'elka-x': 'Cherry Audio', 'polymode': 'Cherry Audio',
    'miniverse': 'Cherry Audio', 'quadra': 'Cherry Audio',
    'sines': 'Cherry Audio', 'surrealistic': 'Cherry Audio',

    # Sonarworks
    'soundid': 'Sonarworks', 'reference': 'Sonarworks',

    # Metric Halo
    'channelstrip': 'Metric Halo', 'haloverb': 'Metric Halo',
    'multiband dynamics': 'Metric Halo', 'transientcontrol': 'Metric Halo',

    # Flux
    'pure limiter': 'Flux', 'pure compressor': 'Flux',
    'syrah': 'Flux', 'epure': 'Flux', 'bittersweet': 'Flux',
    'stereo tool': 'Flux', 'elixir': 'Flux', 'spat revolution': 'Flux',

    # Harrison
    'mixbus': 'Harrison', 'xt-mc': 'Harrison', 'xt-ds': 'Harrison',
    'xt-eg': 'Harrison', 'xt-sc': 'Harrison', 'xt-dc': 'Harrison',
    'xt-bc': 'Harrison', 'xt-lc': 'Harrison', 'xt-me': 'Harrison',
    '32c channel': 'Harrison', 'ava': 'Harrison',

    # --- Sonible (smart / true / pure / proximity / entropy / frei:raum) ---
    'smart:eq': 'Sonible', 'smarteq': 'Sonible', 'smart eq': 'Sonible',
    'smart:eq 3': 'Sonible', 'smart:eq 4': 'Sonible', 'smart eq 3': 'Sonible',
    'smart eq 4': 'Sonible',
    'smart:comp': 'Sonible', 'smartcomp': 'Sonible', 'smart comp': 'Sonible',
    'smart:comp 2': 'Sonible', 'smart comp 2': 'Sonible',
    'smart:limit': 'Sonible', 'smartlimit': 'Sonible', 'smart limit': 'Sonible',
    'smart:reverb': 'Sonible', 'smart reverb': 'Sonible', 'smartreverb': 'Sonible',
    'smart:reverb 2': 'Sonible', 'smart reverb 2': 'Sonible',
    'smart:gate': 'Sonible', 'smart gate': 'Sonible', 'smartgate': 'Sonible',
    'smart:deess': 'Sonible', 'smart deess': 'Sonible', 'smartdeess': 'Sonible',
    'true:balance': 'Sonible', 'true balance': 'Sonible',
    'true:level': 'Sonible', 'true level': 'Sonible',
    'pure:deess': 'Sonible', 'pure deess': 'Sonible',
    'pure:unmask': 'Sonible', 'pure unmask': 'Sonible',
    'pure:eq': 'Sonible', 'pure eq': 'Sonible',
    'pure:comp': 'Sonible', 'pure comp': 'Sonible',
    'pure:verb': 'Sonible', 'pure verb': 'Sonible',
    'pure:limit': 'Sonible', 'pure limit': 'Sonible',
    'proximity:eq+': 'Sonible', 'proximityeq+': 'Sonible',
    'entropy:eq+': 'Sonible', 'entropyeq+': 'Sonible',
    'frei:raum': 'Sonible', 'freiraum': 'Sonible',
    'prime:vocal': 'Sonible', 'prime vocal': 'Sonible',
}

# Паттерны для определения производителя по тексту (CompanyName, Copyright и т.п.)
MANUFACTURER_PATTERNS: Dict[str, str] = {
    r'\bantares\b': 'Antares',
    r'\bauto[-\s]?tune\b': 'Antares',
    r'\bizotope\b': 'iZotope',
    r'\bsoundtoys\b': 'Soundtoys',
    r'\bplugin[-\s]?alliance\b': 'Plugin Alliance',
    r'\bbrainworx\b': 'Plugin Alliance',
    r'\bfabfilter\b': 'FabFilter',
    r'\bvalhalla\b': 'Valhalla DSP',
    r'\boeksound\b': 'Oeksound',
    r'\bwaves\b': 'Waves',
    r'\bacustica\b': 'Acustica Audio',
    r'\bacustica[-\s]?audio\b': 'Acustica Audio',
    r'\bslate[-\s]?digital\b': 'Slate Digital',
    r'\buniversal[-\s]?audio\b': 'Universal Audio',
    r'\buad\b': 'Universal Audio',
    r'\barturia\b': 'Arturia',
    r'\bnative[-\s]?instruments\b': 'Native Instruments',
    r'\bsoftube\b': 'Softube',
    r'\bliquidsonics\b': 'LiquidSonics',
    r'\btokyo[-\s]?dawn\b': 'Tokyo Dawn Records',
    r'\btdr\b': 'Tokyo Dawn Records',
    r'\bik[-\s]?multimedia\b': 'IK Multimedia',
    r'\beventide\b': 'Eventide',
    r'\bmcdsp\b': 'McDSP',
    r'\bsonnox\b': 'Sonnox',
    r'\b2caudio\b': '2CAudio',
    r'\baudio[-\s]?damage\b': 'Audio Damage',
    r'\bacon[-\s]?digital\b': 'Acon Digital',
    r'\bgoodhertz\b': 'Goodhertz',
    r'\bpsp[a-z]*\b': 'PSPaudioware',
    r'\bdmg[a-z]*\b': 'DMGAudio',
    r'\bdmgaudio\b': 'DMGAudio',
    r'\bkilohearts\b': 'Kilohearts',
    r'\bujam\b': 'UJAM',
    r'\bsteinberg\b': 'Steinberg',
    r'\blexicon\b': 'Lexicon',
    r'\btc[-\s]?electronic\b': 'TC Electronic',
    r'\bcelemony\b': 'Celemony',
    r'\boverloud\b': 'Overloud',
    r'\bbaby[-\s]?audio\b': 'Baby Audio',
    r'\baudiothing\b': 'AudioThing',
    r'\bxfer\b': 'Xfer Records',
    r'\bspectrasonics\b': 'Spectrasonics',
    r'\bu[-]?he\b': 'u-he',
    r'\bcableguys\b': 'Cableguys',
    r'\bpolyverse\b': 'Polyverse',
    r'\bblue[-\s]?cat\b': 'Blue Cat Audio',
    r'\bssl\b': 'SSL',
    r'\bsolid[-\s]?state[-\s]?logic\b': 'SSL',
    r'\bzynaptiq\b': 'Zynaptiq',
    r'\bnewfangled\b': 'Newfangled Audio',
    r'\bneural[-\s]?dsp\b': 'Neural DSP',
    r'\bdear[-\s]?reality\b': 'Dear Reality',
    r'\bdevious[-\s]?machines\b': 'Devious Machines',
    r'\bair[-\s]?music\b': 'AIR Music Technology',
    r'\brob[-\s]?papen\b': 'Rob Papen',
    r'\breveal[-\s]?sound\b': 'Reveal Sound',
    r'\blennar\b': 'LennarDigital',
    r'\bsynapse\b': 'Synapse Audio',
    r'\bwaldorf\b': 'Waldorf',
    r'\btal[-\s]': 'TAL-Togu Audio Line',
    r'\bmelda\b': 'MeldaProduction',
    r'\bvoxengo\b': 'Voxengo',
    r'\baudiority\b': 'Audiority',
    r'\boutput\b': 'Output',
    r'\bd16\b': 'D16 Group',
    r'\bglitchmachines\b': 'Glitchmachines',
    r'\bcherry[-\s]?audio\b': 'Cherry Audio',
    r'\bsonarworks\b': 'Sonarworks',
    r'\bmetric[-\s]?halo\b': 'Metric Halo',
    r'\bflux\b': 'Flux',
    r'\bharrison\b': 'Harrison',
    r'\bklanghelm\b': 'Klanghelm',
    r'\bboz\b': 'Boz Digital Labs',
    r'\btbproaudio\b': 'TBProAudio',
    r'\bauburn\b': 'Auburn Sounds',
    r'\bblack[-\s]?rooster\b': 'Black Rooster Audio',
    r'\btone[-\s]?empire\b': 'Tone Empire',
    r'\bleapwing\b': 'Leapwing Audio',
    r'\bvertigo\b': 'Vertigo Sound',
    r'\baccusonus\b': 'Accusonus',
    r'\bfuse[-\s]?audio\b': 'Fuse Audio Labs',
    r'\bsir[-\s]?audio\b': 'SIR Audio Tools',
    r'\banalog[-\s]?obsession\b': 'Analog Obsession',
    r'\bsonible\b': 'Sonible',
}

# Словарь папок -> производитель
FOLDER_TO_MANUFACTURER: Dict[str, str] = {
    'izotope': 'iZotope', 'antares': 'Antares', 'fabfilter': 'FabFilter',
    'waves': 'Waves', 'valhalla': 'Valhalla DSP', 'soundtoys': 'Soundtoys',
    'plugin alliance': 'Plugin Alliance', 'brainworx': 'Plugin Alliance',
    'slate digital': 'Slate Digital', 'universal audio': 'Universal Audio',
    'arturia': 'Arturia', 'native instruments': 'Native Instruments',
    'softube': 'Softube', 'liquidsonics': 'LiquidSonics',
    'tokyo dawn': 'Tokyo Dawn Records', 'ik multimedia': 'IK Multimedia',
    'eventide': 'Eventide', 'mcdsp': 'McDSP', 'sonnox': 'Sonnox',
    'acustica audio': 'Acustica Audio', 'acustica': 'Acustica Audio',
    'celemony': 'Celemony', 'xfer': 'Xfer Records', 'xfer records': 'Xfer Records',
    'spectrasonics': 'Spectrasonics', 'u-he': 'u-he', 'uhe': 'u-he',
    'kilohearts': 'Kilohearts', 'cableguys': 'Cableguys',
    'polyverse': 'Polyverse', 'goodhertz': 'Goodhertz', 'oeksound': 'Oeksound',
    'pspaudioware': 'PSPaudioware', 'psp': 'PSPaudioware',
    'dmgaudio': 'DMGAudio', 'dmg audio': 'DMGAudio',
    'audio damage': 'Audio Damage', 'acon digital': 'Acon Digital',
    '2caudio': '2CAudio', 'overloud': 'Overloud', 'blue cat': 'Blue Cat Audio',
    'steinberg': 'Steinberg', 'ssl': 'SSL', 'solid state logic': 'SSL',
    'zynaptiq': 'Zynaptiq', 'newfangled': 'Newfangled Audio',
    'neural dsp': 'Neural DSP', 'dear reality': 'Dear Reality',
    'ujam': 'UJAM', 'baby audio': 'Baby Audio', 'audiothing': 'AudioThing',
    'rob papen': 'Rob Papen', 'reveal sound': 'Reveal Sound',
    'lennardigital': 'LennarDigital', 'synapse audio': 'Synapse Audio',
    'waldorf': 'Waldorf', 'tal': 'TAL-Togu Audio Line',
    'meldaproduction': 'MeldaProduction', 'melda': 'MeldaProduction',
    'sonible': 'Sonible',
}

VST2_PATHS: List[Path] = [
    Path(r"C:\Program Files\Common Files\Steinberg\VST2"),
    Path(r"C:\Program Files (x86)\VstPlugins"),
    Path(r"C:\Program Files (x86)\Steinberg\VstPlugins"),
    Path(os.path.expandvars(r"%USERPROFILE%\Documents\VST")),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\VST")),
]

VST3_STANDARD_PATHS: List[Path] = [
    Path(r"C:\Program Files\Common Files\VST3"),
    Path(r"C:\Program Files (x86)\Common Files\VST3"),
]

VST3_USER_PATHS: List[Path] = [
    Path(os.path.expandvars(r"%USERPROFILE%\Documents\VST3")),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\VST3")),
    Path(os.path.expandvars(r"%APPDATA%\VST3")),
]

# ==============================================================================  
# DATA CLASSES & UTILS  
# ==============================================================================  

# Whitelist коротких ключей, которым можно доверять в match_name
SHORT_NAME_WHITELIST: Set[str] = {
    'rx', 'nx', 'vmr', 'vms', 'vbc', 'vcc', 'ba-1', 'b2', 'b3',
    'l1', 'l2', 'l3', 'dc8c', 'dc1a', 'mjuc', 'ott'
}


class VSTDatabase:
    """Encapsulates manufacturer data and matching logic."""
    def __init__(self):
        self.name_map = PLUGIN_NAME_TO_MANUFACTURER
        self.folder_map = FOLDER_TO_MANUFACTURER
        self.patterns = [
            (re.compile(p, re.IGNORECASE), m)
            for p, m in MANUFACTURER_PATTERNS.items()
        ]

    def match_name(self, name: str) -> Optional[str]:
        """
        Поиск производителя по имени плагина.
        Приоритет: сырое имя (для bx_ и т.п.), затем очищенное от пробелов/дефисов.
        Слишком короткие/общие ключи игнорируются, кроме whitelist.
        """
        name_lower = name.lower()
        # подчёркивания не трогаем (для bx_ и tal-)
        name_clean = re.sub(r'[\-\s]+', ' ', name_lower).strip()

        for key, mfr in self.name_map.items():
            kl = key.lower()
            # пропускаем слишком короткие ключи, кроме whitelist
            plain = re.sub(r'[\s\-\_:]+', '', kl)
            if len(plain) < 4 and kl not in SHORT_NAME_WHITELIST:
                continue

            kc = re.sub(r'[\-\s]+', ' ', kl).strip()

            # 1) сырое имя (важно для bx_, tal- и т.п.)
            if kl in name_lower:
                return mfr

            # 2) очищенное (важно для virtual mix rack, smart eq и т.п.)
            if kc and kc in name_clean:
                return mfr

        return None

    def match_pattern(self, text: str) -> Optional[str]:
        for pattern, mfr in self.patterns:
            if pattern.search(text):
                return mfr
        return None

    def match_folder(self, path: Path) -> Optional[str]:
        path_parts = str(path).lower()
        for key, mfr in self.folder_map.items():
            if key in path_parts:
                return mfr
        for part in path.parts:
            part_lower = part.lower()
            if part_lower in self.folder_map:
                return self.folder_map[part_lower]
            for key, mfr in self.folder_map.items():
                if key in part_lower:
                    return mfr
        return None

    def clean_manufacturer(self, name: str) -> str:
        if not name:
            return "Unknown"
        name = name.strip().rstrip(',').rstrip('.').strip()
        name = re.sub(r'\s+(Inc\.?|LLC\.?|Ltd\.?|GmbH|Corp\.?|Co\.?)$', '',
                      name, flags=re.IGNORECASE)
        name = re.sub(r'^(Copyright|©|\(c\))\s*\d*\s*', '',
                      name, flags=re.IGNORECASE)
        if not name or len(name) < 2:
            return "Unknown"
        for pattern, normalized in self.patterns:
            if pattern.search(name):
                return normalized
        return name

    def search_binary(self, data: bytes) -> Optional[str]:
        # сначала пробуем regex-паттерны производителей
        for pattern, mfr in MANUFACTURER_PATTERNS.items():
            try:
                if re.search(pattern.encode('ascii', errors='ignore'),
                            data, re.IGNORECASE):
                    return mfr
            except Exception:
                pass

        # затем несколько популярных брендов простым поиском
        popular = [
            (b'iZotope', 'iZotope'), (b'Antares', 'Antares'),
            (b'FabFilter', 'FabFilter'), (b'Waves', 'Waves'),
            (b'Valhalla', 'Valhalla DSP'), (b'Soundtoys', 'Soundtoys'),
            (b'Plugin Alliance', 'Plugin Alliance'),
            (b'Brainworx', 'Plugin Alliance'),
            (b'Slate Digital', 'Slate Digital'),
            (b'Universal Audio', 'Universal Audio'),
            (b'Arturia', 'Arturia'),
            (b'Native Instruments', 'Native Instruments'),
            (b'Softube', 'Softube'),
            (b'LiquidSonics', 'LiquidSonics'),
            (b'Eventide', 'Eventide'),
            (b'Celemony', 'Celemony'),
            (b'Oeksound', 'Oeksound'),
            (b'Goodhertz', 'Goodhertz'),
            (b'Baby Audio', 'Baby Audio'),
            (b'Kilohearts', 'Kilohearts'),
            (b'Xfer Records', 'Xfer Records'),
            (b'u-he', 'u-he'),
            (b'Cableguys', 'Cableguys'),
            (b'DMGAudio', 'DMGAudio'),
            (b'PSPaudioware', 'PSPaudioware'),
            (b'Acustica Audio', 'Acustica Audio'),
            (b'sonible', 'Sonible'),
        ]
        for pattern, mfr in popular:
            if pattern in data:
                return mfr
        return None


class ProgressBar:
    """Simple text-based progress bar."""
    def __init__(self, total: int, width: int = 40):
        self.total = total
        self.width = width
        self.current = 0

    def update(self, increment: int = 1):
        self.current += increment
        self._print()

    def _print(self):
        percent = (min(100, int(100 * self.current / self.total))
                   if self.total > 0 else 100)
        filled = int(self.width * percent / 100)
        bar = '=' * filled + '-' * (self.width - filled)
        sys.stdout.write(f'\r[{bar}] {percent}% ({self.current}/{self.total})')
        sys.stdout.flush()

    def finish(self):
        self.current = self.total
        self._print()
        sys.stdout.write('\n')


@dataclass(frozen=True)
class PluginInfo:
    manufacturer: str
    name: str
    plugin_type: str
    arch: str = "Unknown"
    path: str = ""

    def to_dict(self):
        return asdict(self)


# ==============================================================================  
# MAIN SCANNER CLASS  
# ==============================================================================  

@dataclass
class VSTScanner:
    plugins: List[PluginInfo] = field(default_factory=list)
    scanned_paths: Set[str] = field(default_factory=set)
    verbose: bool = False
    unknown_plugins: List[PluginInfo] = field(default_factory=list)
    db: VSTDatabase = field(default_factory=VSTDatabase)

    def __post_init__(self) -> None:
        self.vst3_paths = self._get_all_vst3_paths()
        self.vst2_paths = self._get_all_vst2_paths()

    def _get_registry_paths(self, key_path: str,
                            value_name: str = "VSTPluginsPath") -> List[Path]:
        """Читает пути из реестра Windows."""
        paths: List[Path] = []
        for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                with winreg.OpenKey(root, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, value_name)
                    if value:
                        for p in value.split(';'):
                            if p.strip():
                                paths.append(Path(p.strip()))
            except OSError:
                pass
        return paths

    def _get_all_vst3_paths(self) -> List[Path]:
        """Собирает все возможные пути VST3."""
        paths: Set[Path] = set()
        paths.update(VST3_STANDARD_PATHS)
        paths.update(VST3_USER_PATHS)

        # Добавляем подпапки производителей
        for base in VST3_STANDARD_PATHS:
            if base.exists():
                try:
                    for subdir in base.iterdir():
                        if subdir.is_dir():
                            paths.add(subdir)
                except PermissionError:
                    pass

        return [p for p in paths if p.exists()]

    def _get_all_vst2_paths(self) -> List[Path]:
        """Собирает все возможные пути VST2."""
        paths: Set[Path] = set()
        paths.update(VST2_PATHS)

        # Пути из реестра
        paths.update(self._get_registry_paths(r"SOFTWARE\VST",
                                              "VSTPluginsPath"))
        paths.update(self._get_registry_paths(
            r"SOFTWARE\Steinberg\VST Plugins Path"))

        return [p for p in paths if p.exists()]

    def _extract_pe_metadata(self, file_path: Path) -> Dict[str, str]:
        """Метод: извлечение метаданных из PE файла."""
        if not PEFILE_AVAILABLE:
            return {}

        try:
            pe = pefile.PE(str(file_path), fast_load=True)
            pe.parse_data_directories(directories=[
                pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']
            ])

            metadata: Dict[str, str] = {}

            if hasattr(pe, 'FileInfo'):
                for file_info_list in pe.FileInfo:
                    for file_info in file_info_list:
                        if hasattr(file_info, 'StringTable'):
                            for st in file_info.StringTable:
                                for entry in st.entries.items():
                                    key = entry[0].decode(
                                        'utf-8', errors='ignore')
                                    value = entry[1].decode(
                                        'utf-8', errors='ignore')
                                    if value.strip():
                                        metadata[key] = value.strip()

            pe.close()
            return metadata
        except Exception as e:
            if self.verbose:
                print(f"  PE error for {file_path.name}: {e}")
            return {}

    def _parse_vst3_moduleinfo(self, vst3_path: Path) -> Dict[str, str]:
        """Метод: парсинг moduleinfo.json для VST3."""
        moduleinfo = vst3_path / "Contents" / "Resources" / "moduleinfo.json"
        if moduleinfo.exists():
            try:
                with open(moduleinfo, 'r', encoding='utf-8',
                          errors='ignore') as f:
                    data = json.load(f)
                return {
                    'Vendor': data.get('Vendor', data.get('Manufacturer', '')),
                    'Name': data.get('Name', '')
                }
            except Exception:
                pass
        return {}

    def _parse_vst3_plist(self, vst3_path: Path) -> Dict[str, str]:
        """Метод: парсинг Info.plist для VST3."""
        plist = vst3_path / "Contents" / "Info.plist"
        if not plist.exists():
            return {}

        try:
            tree = ET.parse(plist)
            root = tree.getroot()
            dict_elem = root.find('dict')
            if dict_elem is None:
                return {}

            plist_dict: Dict[str, str] = {}
            key_elem = None
            for elem in dict_elem:
                if elem.tag == 'key':
                    key_elem = elem.text or ""
                elif elem.tag in ('string', 'real', 'integer') and key_elem:
                    plist_dict[key_elem] = elem.text or ""
                    key_elem = None

            return plist_dict
        except Exception:
            return {}

    def _determine_manufacturer(self, file_path: Path,
                                plugin_type: str) -> Tuple[str, str]:
        """
        Комплексное определение производителя с приоритетами.
        Возвращает (manufacturer, name).

        Приоритеты (от более честных к менее честным):
        1) Имя плагина (ручной маппинг)
        2) VST3 moduleinfo.json / Info.plist
        3) PE-метаданные
        4) Regex по имени
        5) Бинарный поиск
        6) Папка (как самый последний резерв)
        """
        default_name = (file_path.stem
                        .replace('.vst3', '')
                        .replace('.dll', ''))
        name = default_name

        # WaveShell — всегда Waves, но только для самого WaveShell
        if 'waveshell' in default_name.lower():
            return 'Waves', default_name

        # === 1: По имени плагина ===
        manufacturer = self.db.match_name(default_name)
        if manufacturer:
            return manufacturer, name

        dll_candidates: List[Path] = []
        if plugin_type == "VST3" and file_path.is_dir():
            for arch_dir in ["x86_64-win", "x86-win"]:
                dll_path = (file_path / "Contents" / arch_dir /
                            (file_path.stem + ".vst3"))
                if dll_path.exists():
                    dll_candidates.append(dll_path)
        elif file_path.is_file():
            dll_candidates.append(file_path)

        # === 2: Для VST3 — moduleinfo.json ===
        if plugin_type == "VST3" and file_path.is_dir():
            module_data = self._parse_vst3_moduleinfo(file_path)
            if module_data.get('Vendor'):
                vendor = self.db.clean_manufacturer(module_data['Vendor'])
                if vendor != "Unknown":
                    name = module_data.get('Name', default_name) or default_name
                    return vendor, name

            # === 3: Info.plist ===
            plist_data = self._parse_vst3_plist(file_path)
            if plist_data:
                copyright_str = plist_data.get(
                    'NSHumanReadableCopyright', '')
                if copyright_str:
                    manufacturer = self.db.match_pattern(copyright_str)
                    if manufacturer:
                        name = plist_data.get(
                            'CFBundleName', default_name) or default_name
                        return manufacturer, name

        # === 4: PE Metadata ===
        for dll in dll_candidates:
            metadata = self._extract_pe_metadata(dll)
            if not metadata:
                continue

            for key in ['CompanyName', 'LegalTrademarks',
                        'LegalCopyright', 'ProductName']:
                value = metadata.get(key, '')
                if not value:
                    continue

                # сначала паттерны по производителям
                manufacturer = self.db.match_pattern(value)
                if manufacturer:
                    prod_name = metadata.get(
                        'ProductName',
                        metadata.get('FileDescription', default_name))
                    return manufacturer, (prod_name or default_name)

                # затем аккуратно берём CompanyName "как есть"
                if key == 'CompanyName':
                    cleaned = self.db.clean_manufacturer(value)
                    if cleaned != "Unknown" and len(cleaned) > 2:
                        prod_name = metadata.get('ProductName', default_name)
                        return cleaned, (prod_name or default_name)

        # === 5: Regex по имени ===
        manufacturer = self.db.match_pattern(default_name)
        if manufacturer:
            return manufacturer, name

        # === 6: Быстрый бинарный поиск ===
        if dll_candidates:
            binary_mfr = self.db.search_binary(
                self._read_binary_head(dll_candidates[0]))
            if binary_mfr:
                return binary_mfr, name

        # === 7: Папки (самый ненадёжный источник, в самом конце) ===
        manufacturer = self.db.match_folder(file_path)
        if manufacturer:
            return manufacturer, name

        return "Unknown", name

    def _read_binary_head(self, file_path: Path,
                          size: int = 256 * 1024) -> bytes:
        try:
            if file_path.stat().st_size > 20 * 1024 * 1024:
                return b""
            with open(file_path, 'rb') as f:
                return f.read(size)
        except Exception:
            return b""

    @staticmethod
    def _get_pe_architecture(file_path: Path) -> str:
        """Определяет архитектуру PE файла."""
        try:
            with open(file_path, 'rb') as f:
                if f.read(2) != b'MZ':
                    return "Unknown"
                f.seek(0x3C)
                pe_offset = struct.unpack('<I', f.read(4))[0]
                f.seek(pe_offset)
                if f.read(4) != b'PE\0\0':
                    return "Unknown"
                machine = struct.unpack('<H', f.read(2))[0]
                return ("x64" if machine == 0x8664
                        else "x86" if machine == 0x014c
                        else "Unknown")
        except Exception:
            return "Unknown"

    def extract_vst3_info(self, file_path: Path) -> PluginInfo:
        """Извлекает информацию о VST3 плагине."""
        arch = "Unknown"
        if file_path.is_dir():
            for arch_dir, arch_name in [("x86_64-win", "x64"),
                                        ("x86-win", "x86")]:
                dll = file_path / "Contents" / arch_dir / (file_path.stem + ".vst3")
                if dll.exists():
                    arch = arch_name
                    break
        else:
            arch = self._get_pe_architecture(file_path)

        manufacturer, name = self._determine_manufacturer(file_path, "VST3")
        return PluginInfo(manufacturer, name, "VST3", arch, str(file_path))

    def extract_vst2_info(self, file_path: Path) -> PluginInfo:
        """Извлекает информацию о VST2 плагине."""
        arch = self._get_pe_architecture(file_path)
        manufacturer, name = self._determine_manufacturer(file_path, "VST2")
        return PluginInfo(manufacturer, name, "VST2", arch, str(file_path))

    def _discover_files(self) -> List[Tuple[Path, str]]:
        """Phase 1: Discover all candidate files."""
        candidates: List[Tuple[Path, str]] = []

        # VST3
        for path in self.vst3_paths:
            try:
                for item in path.rglob('*.vst3'):
                    candidates.append((item, "VST3"))
            except Exception:
                pass

        # VST2
        for path in self.vst2_paths:
            try:
                for item in path.rglob('*.dll'):
                    candidates.append((item, "VST2"))
            except Exception:
                pass

        return candidates

    def _process_file(self, item: Tuple[Path, str]) -> Optional[PluginInfo]:
        """Process a single file."""
        path, ptype = item
        try:
            resolved = path.resolve()
            str_resolved = str(resolved)

            # простая защита от повторной обработки одного и того же файла
            if str_resolved in self.scanned_paths:
                return None
            self.scanned_paths.add(str_resolved)

            if ptype == "VST3":
                return self.extract_vst3_info(resolved)
            else:
                return self.extract_vst2_info(resolved)
        except Exception:
            return None

    def scan_all_plugins(self, max_workers: int = 8) -> None:
        """Сканирует все плагины."""
        print("🔍 Начинаю сканирование плагинов...")
        print(f"📂 VST3 путей: {len(self.vst3_paths)}, "
              f"VST2 путей: {len(self.vst2_paths)}\n")

        # Phase 1: Discovery
        print("⏳ Поиск файлов (Phase 1/2)...")
        files = self._discover_files()
        print(f"   Найдено кандидатов: {len(files)}")

        if not files:
            print("   Плагины не найдены.")
            return

        # Phase 2: Processing
        print(f"🚀 Обработка файлов (Phase 2/2)...")
        progress = ProgressBar(len(files))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self._process_file, f): f
                for f in files
            }

            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    if result:
                        self.plugins.append(result)
                except Exception as e:
                    if self.verbose:
                        print(f"  ⚠️ Task error: {e}")
                finally:
                    progress.update()

        progress.finish()

        # Удаляем дубликаты и сортируем
        unique: Dict[Tuple[str, str, str], PluginInfo] = {}
        for p in self.plugins:
            key = (p.name.lower(), p.plugin_type, p.path)
            if key not in unique:
                unique[key] = p

        self.plugins = sorted(unique.values(),
                              key=lambda x: (x.manufacturer.lower(),
                                             x.name.lower()))

        # Собираем unknown
        self.unknown_plugins = [
            p for p in self.plugins if p.manufacturer == "Unknown"
        ]

        print(f"\n✅ Найдено уникальных плагинов: {len(self.plugins)}")
        print(f"❓ Unknown производителей: {len(self.unknown_plugins)}")

    def write_to_txt(self, output_file: str) -> None:
        """Сохраняет результаты в TXT."""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"{'Manufacturer':<45} | {'Plugin':<50} | "
                    f"{'Type':<4} | {'Arch':<4}\n")
            f.write(f"{'-'*45}+{'-'*52}+{'-'*6}+{'-'*6}\n")

            for plugin in self.plugins:
                mfr = plugin.manufacturer[:45].ljust(45)
                name = plugin.name[:50].ljust(50)
                f.write(f"{mfr} | {name} | "
                        f"{plugin.plugin_type:<4} | {plugin.arch:<4}\n")
        print(f"💾 Saved: {output_file}")

    def write_unknown_to_txt(self, output_file: str) -> None:
        """Сохраняет unknown плагины для анализа."""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Unknown manufacturer plugins - check paths for clues\n\n")
            for plugin in self.unknown_plugins:
                f.write(f"Name: {plugin.name}\n")
                f.write(f"Path: {plugin.path}\n")
                f.write(f"Type: {plugin.plugin_type}\n")
                f.write("-" * 80 + "\n")
        print(f"💾 Unknown plugins saved: {output_file}")

    def write_to_json(self, output_file: str) -> None:
        """Сохраняет в JSON."""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([p.to_dict() for p in self.plugins],
                      f, indent=2, ensure_ascii=False)
        print(f"💾 Saved: {output_file}")

    def write_to_csv(self, output_file: str) -> None:
        """Сохраняет в CSV."""
        with open(output_file, "w", encoding="utf-8", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Manufacturer", "Name",
                             "Type", "Arch", "Path"])
            for p in self.plugins:
                writer.writerow([p.manufacturer, p.name,
                                 p.plugin_type, p.arch, p.path])
        print(f"💾 Saved: {output_file}")

    def print_stats(self) -> None:
        """Статистика."""
        mfr_count: Dict[str, int] = {}
        for p in self.plugins:
            mfr_count[p.manufacturer] = mfr_count.get(p.manufacturer, 0) + 1

        vst3 = sum(1 for p in self.plugins if p.plugin_type == "VST3")
        vst2 = len(self.plugins) - vst3
        x64 = sum(1 for p in self.plugins if p.arch == "x64")
        x86 = sum(1 for p in self.plugins if p.arch == "x86")
        unknown = mfr_count.get("Unknown", 0)

        print("\n📊 Статистика:")
        print(f"   Производителей: {len(mfr_count)}")
        print(f"   VST3: {vst3} | VST2: {vst2}")
        print(f"   x64: {x64} | x86: {x86}")
        if self.plugins:
            print(f"   Unknown: {unknown} "
                  f"({100*unknown/len(self.plugins):.1f}%)")
        else:
            print(f"   Unknown: {unknown}")

        top = sorted(mfr_count.items(),
                     key=lambda x: x[1], reverse=True)[:25]
        print("\n   🏆 Топ-25 производителей:")
        for i, (mfr, count) in enumerate(top, 1):
            print(f"     {i:2d}. {mfr:<45} {count:3d}")


def main() -> None:
    parser = argparse.ArgumentParser(description="VST Plugin Scanner v7.1")
    parser.add_argument("--output", "-o", default="plugins",
                        help="Output base name")
    parser.add_argument("--json", action="store_true", help="Export JSON")
    parser.add_argument("--csv", action="store_true", help="Export CSV")
    parser.add_argument("--txt", action="store_true", default=True)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--no-txt", dest="txt", action="store_false")
    args = parser.parse_args()

    print("=" * 80)
    print("🎛️  VST Plugin Scanner v7.1 - Safer Manufacturer Detection")
    print("=" * 80 + "\n")

    scanner = VSTScanner(verbose=args.verbose)
    scanner.scan_all_plugins()

    base = Path(__file__).parent / args.output

    if args.txt:
        scanner.write_to_txt(str(base) + ".txt")
        scanner.write_unknown_to_txt(str(base) + "_unknown.txt")
    if args.json:
        scanner.write_to_json(str(base) + ".json")
    if args.csv:
        scanner.write_to_csv(str(base) + ".csv")

    scanner.print_stats()

    print("\n" + "=" * 80)
    print("✅ Сканирование завершено!")
    print("=" * 80)


if __name__ == "__main__":
    main()
