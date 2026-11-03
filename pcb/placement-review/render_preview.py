"""Render the KiCad SVG export, with readable labels on the rough-placement view.

Uses PyMuPDF from the existing temporary PDF-tools directory. This draws no PCB
geometry; rough.svg is exported directly from ts52k.kicad_pcb by kicad-cli.
"""
from pathlib import Path
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.environ['TEMP'], 'ts52k-pdf-tools'))
import pymupdf

OUT = Path(__file__).resolve().parent
svg = ET.parse(OUT / 'rough.svg').getroot()
ns = '{http://www.w3.org/2000/svg}'
def label(x,y,text,size=1.1):
    ET.SubElement(svg, ns+'rect', {'x':str(x-.25),'y':str(y-size),
        'width':str(len(text)*size*.62+.5),'height':str(size*1.3),
        'fill':'white','fill-opacity':'.94'})
    node = ET.SubElement(svg, ns+'text', {'x':str(x),'y':str(y),
        'font-family':'sans-serif','font-size':str(size),'font-weight':'bold',
        'fill':'#101820','stroke':'none'})
    node.text = text

# KiCad export coordinates: board x + 3.6369 mm, board y - 41.0854 mm.
ET.SubElement(svg,ns+'rect',{'x':'33.5869','y':'16.6646','width':'3.8','height':'10.5',
    'fill':'#f6a523','fill-opacity':'0.20','stroke':'#b56b00','stroke-width':'0.2'})
label(23.2,21.0,'MDBT50Q',1.25)
label(23.2,22.8,'15.5 x 10.5 mm',.95)
label(23.2,24.4,'U5 / B.Cu',.95)
label(23.7,4.0,'USB / J1',1.1)
label(31.0,11.8,'Charger / U6',1.0)
label(5.0,25.5,'X3 / 32.768 kHz',.9)
label(4.8,18.0,'REG0 / VDDH / VDD',.9)
label(4.5,9.0,'VBUS filter',.85)
label(12.0,30.6,'MX3 pad 2: module clear by 2.68 mm in X',.8)
label(38.0,22.5,'D2 relocated',.85)
label(25.0,42.5,'SWD / J2',.9)
label(47.5,33.0,'Reset / SW1',.9)
label(13.5,48.0,'BAT / J3: cable to left',1.0)
# Dashed arrows are reserved wiring / cable directions, not routed PCB copper.
ET.SubElement(svg,ns+'path',{'d':'M 22.2,9.2 L 22.2,15.6 L 23.45,17.2 M 23.1,16.4 L 23.45,17.2 L 22.6,16.9',
    'fill':'none','stroke':'#aa2020','stroke-width':'.18','stroke-dasharray':'.7 .4'})
label(17.8,14.6,'USB pair corridor',.75)
ET.SubElement(svg,ns+'rect',{'x':'25.2','y':'25.15','width':'6.9','height':'2.4',
    'fill':'#38ad72','fill-opacity':'.22','stroke':'#14753a','stroke-width':'.15'})
ET.SubElement(svg,ns+'path',{'d':'M 41,29.1 L 29.8,29.1 L 29.8,27.5 M 29.3,28.3 L 29.8,27.5 L 30.3,28.3',
    'fill':'none','stroke':'#14753a','stroke-width':'.22','stroke-dasharray':'.8 .5'})
label(30.4,31.1,'Plan: 10 rows + encoder A/B to pads 3-14',.75)
ET.SubElement(svg,ns+'path',{'d':'M 14.5,40.9 L 8.0,40.9 M 9,40.4 L 8,40.9 L 9,41.4',
    'fill':'none','stroke':'#984a00','stroke-width':'.25','stroke-dasharray':'.8 .5'})
label(2.0,55.0,'ROUGH PLACEMENT - no new routing',1.25)
label(2.0,56.8,'Arrows = planned corridors; GPIO nets still old',.85)
label(2.0,58.3,'Top-view coordinates; parts on back; antenna shaded orange',.8)
annotated=ET.tostring(svg,encoding='utf-8',xml_declaration=True)
doc=pymupdf.open(stream=annotated,filetype='svg')
pdf=pymupdf.open('pdf',doc.convert_to_pdf())
page=pdf[0]
page.get_pixmap(matrix=pymupdf.Matrix(3,3)).save(OUT/'overview.png')
crop=pymupdf.Rect(0,0,67*72/25.4,60*72/25.4)
page.get_pixmap(matrix=pymupdf.Matrix(6,6),clip=crop).save(OUT/'mcu-area.png')
print('Rendered overview.png and mcu-area.png from actual PCB SVG')
