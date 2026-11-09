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

label(2.0,55.0,'MATRIX JOINS / 2026-11-08',1.25)
label(2.0,57.0,'column lanes revised; col4 / col2 / col1 joined; 13 remain',.85)
annotated=ET.tostring(svg,encoding='utf-8',xml_declaration=True)
doc=pymupdf.open(stream=annotated,filetype='svg')
pdf=pymupdf.open('pdf',doc.convert_to_pdf())
page=pdf[0]
page.get_pixmap(matrix=pymupdf.Matrix(3,3)).save(OUT/'overview.png')
crop=pymupdf.Rect(0,0,67*72/25.4,60*72/25.4)
page.get_pixmap(matrix=pymupdf.Matrix(6,6),clip=crop).save(OUT/'mcu-area.png')
print('Rendered overview.png and mcu-area.png from actual PCB SVG')
