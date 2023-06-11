#!/usr/bin/env python

import errno
import xml.etree.ElementTree as ET
import urllib.parse
import re
import os, shutil  # make dir and copy files
import base64
import sys, getopt
# lxml is only used for cleaning the CDATA html. Con: not part of Python default install
import lxml
from lxml.html import fromstring, tostring, clean
from lxml import objectify

"""
Clase para leer/convertir aquellos ficheros
que tienen una estructura en formato QTI/IMS, y través de las equivalencias
crea el fichero en formato MoodleXML.
"""
class QTI2moodle():


    """
    Inicializar los atributos de los objetos pertenecientes a la clase QTI2moodle
    """
    def __init__(self, file_input, out, path_out):
        
        self.file_input = file_input #Fichero de entrada
        self.out = out #Nombre del fichero de salida
        self.path_out = path_out #Ruta que almacenará el fichero de salida

    

    """
    Función que lee el fichero de entrada en formato QTI, y a través de las 
    equivalencias y las demás funciones  de la clase, crea el fichero 
    de salida en formato moodleXML.
    """
    def readQTI(self,inputfile, outputfolder):


        filename = inputfile
        error_message = None

        #Obtenemos el arbol xml de QTI
        try:
            tree = objectify.parse(filename)
        except Exception as e:
            error_message = f'An error occurred in reading the quiz file. Technical details:\n\t{e}'
            print(error_message)

        root = tree.getroot()


        #Desglosamos los elementos del arbol XML de QTI/IMS
        titleArc=root.assessment.attrib["title"]

        items =  tree.findall('.//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}item')
              
      
        if len(items)==0:
            print("No hay prgeuntas para convertir")
            return 0

      
        #Creamos el arbol correspondiente al fichero de salida en formato moodleXML
        quiz = ET.Element("quiz")

        only=0

        #Recorremos los items(preguntas) del cuestionario 
        for item in items:

            ######## Cada item esta dividido como minimo en tres partes
            itemdata = item.itemmetadata.qtimetadata.getchildren()

            itempresentation =  item.presentation.getchildren() #tiene dos hijos (material=0, response_lid=1)

            itemresprocessing = item.resprocessing.getchildren()
            ########


            qtidata = []
            #Obtenemos los valores de los metadatos
            for data in itemdata:
                qtidata.append(data.fieldentry)

            #Estos son los unicos valores de [qtidata] que contienen equivalencia en el formato moodleXML
            qtype = qtidata[0]
            point = qtidata[1]


            ########

            question=itempresentation[0].mattext #Contenido de la pregunta
            pos_aw = []
            correctChoiceID = []


            #Realizamos un pre-procesamineto para obtener ciertos elementos antes de convertir cada pregunta
            if qtype == 'short_answer_question' or qtype == 'multiple_choice_question' or qtype == 'multiple_answers_question' or qtype == 'true_false_question':
                for i in range(1,len(itemresprocessing)): #Recorremos los procedimientos de la pregunta
                    if itemresprocessing[i].attrib['continue']=="No": #Y solo nos interesa aquel 'para' el procesamiento, ya que siginifca que es la respuesta correcta

                        score = str(itemresprocessing[i].setvar).strip() #Obtenemos la puntuación de la respuesta

                        if len(itemresprocessing[i].conditionvar.getchildren()) == 1 and  qtype != 'multiple_answers_question':
                            #Guardamos el ID de la respuesta correcta (cuando solo hay UNA correcta)
                            haveAnd = itemresprocessing[i].conditionvar.getchildren()
                            if str(haveAnd[0].attrib) != "{}":                   
                                correctChoiceID.append( str(itemresprocessing[i].conditionvar.varequal).strip()) 
                            else:
                                correctChoiceID.append( str(haveAnd[0].varequal).strip()) 

                        elif len(itemresprocessing[i].conditionvar.getchildren()) > 1 and qtype != 'multiple_answers_question': 
                            #En el caso de que haya más de una, guardamos las posibles respuestas  
                            for aw in itemresprocessing[i].conditionvar.getchildren():
                                pos_aw.append(aw)
                        else:
                            #En el caso de que la pregunta sea multi respuesta, guardamos todas las respuestas correctas
                            answ=itemresprocessing[i].conditionvar.getchildren()
                            children=answ[0].getchildren()
                            for element in children:
                                if str(element.attrib) != "{}": 
                                    correctChoiceID.append(element)

            

            ############## Para una mejor subida del fichero a moodle, añadimos una categoria
            if only==0:
                quiz = self.makeCategoria(quiz,titleArc)
                only = only+1
            #############

            
            prefix = self.getprefix(qtype) #Obtenemos el prefijo correspondiente para el nombre del fichero de salida

            question= self.fixHtmlText(question) #Pasamos el valor de la pregunta a formato html
            
            #Procedemos a convertir la pregunta dependiendo de su tipo
            try:
                if qtype == 'short_answer_question':
                    questionMask = ET.SubElement(quiz,"question",  type= "shortanswer")
                    self.produceSAQuestion(questionMask,item,question ,pos_aw, point,score)
        #--------------------------------------------------------
                    
                if qtype == 'multiple_choice_question' or qtype=='multiple_answers_question':

                    questionMask = ET.SubElement(quiz,"question",  type= "multichoice")
                    choices = itempresentation[1].render_choice.getchildren()
                    self.produceMCQuestion(questionMask,item,question ,choices,correctChoiceID, point,score)
        #--------------------------------------------------------

                if qtype == 'true_false_question':
                    choices = itempresentation[1].render_choice.getchildren()
                    questionMask = ET.SubElement(quiz,"question",  type= "truefalse")
                    self.produceTFQuestion(questionMask,item,question ,choices,correctChoiceID, point,score)
        #--------------------------------------------------------
        #       
                if qtype == 'matching_question':
                    questionMask = ET.SubElement(quiz,"question",  type= "matching")

                    subquestion = []
                    choices = []

                    for i in range(1,len(itempresentation)):#Columna izquierda
                        subquestion.append(itempresentation[i].material.mattext)
                        
                    for aw in itempresentation[1].render_choice.getchildren():#Columna derecha
                        choices.append(aw.material.mattext)
        

                    self.produceMATCHQuestion(questionMask,item,question ,subquestion, choices, point)
        #--------------------------------------------------------        

                if qtype == 'numerical_question':
                    scores =[]
                    choices = []
                    tolerancias = []
                    tipoUnidades = itempresentation[1].render_fib.attrib['fibtype']

                    for i in range(1,len(itemresprocessing)):#Empezamos desde el hijo 1, ya que el 0 es outcomes 
                        info = itemresprocessing[i].getchildren()
                    
                        sc = info[1] #Score
                        naw = info[0].getchildren() #Condiciones 

                        #Obtenemos el valor exacto de la respuesta y el error permitido 
                        if len(naw)==1:
                            valores=naw[0].getchildren()
                            exacto = valores[0] 
                            dif = valores[1]
                            error = round(float(dif.varlte)-float(exacto),5)
                        else:
                            exacto=sum(naw)/2
                            error = round(float(naw[1])-float(exacto),5)

                        scores.append(sc)
                        choices.append(exacto)
                        tolerancias.append(error)

                    questionMask = ET.SubElement(quiz,"question",  type= "numerical")
                    self.produceNUMQuestion(questionMask,item,question ,choices,tolerancias, point,scores,tipoUnidades)
        #--------------------------------------------------------        

            except e:
                print("Error in produce: ", qtype)
                print("Details: ", e)
                return -1  
            

        #Creamos el fichero de salida    
        self.out =prefix+'_'+self.out+'.xml'
        filename = outputfolder+'/'+ self.out
        self.writequestionfile(quiz, filename)



    """
    Función que crea la categoría usando el titulo del cuestionarios, esto 
    puede ser útil al importar o exportar el cuestionario, ya que permite 
    clasificar y organizar las preguntas en categorías predefinidas.
    """
    def makeCategoria(self,quiz,title):

        question = ET.SubElement(quiz, "question", type="category")

        category = ET.SubElement(question, "category")
        categoryText = ET.SubElement(category, "text")
        texto = "$course$/top/Valor por defecto para "+ str(title) 
        categoryText.text = texto

        info = ET.SubElement(question, "info", format = "moodle_auto_format")
        infoText = ET.SubElement ( info, "text")
        texto = "Categoría por defecto para preguntas compartidas en el contexto [ "+  str(title) + " ]"
        infoText.text = texto

        idnumber = ET.SubElement(question, "idnumber")

        return quiz
    
    """
    Función que obtiene un prefijo según el tipo de pregunta
    """
    def getprefix(self,qtype):
        prefix = 'AAA_ERROR'

        if qtype == 'short_answer_question':
            prefix = 'MSHORT_'

        if qtype == 'numerical_question':
            prefix = 'NUMERIC_'
            
        if qtype == 'matching_question':
            prefix = 'MARCHING_'

        if qtype == 'multiple_choice_question' or qtype == 'multiple_answers_question':
            prefix = "MULTI_"

        if qtype == 'true_false_question':    
            prefix = "TR_FL_"
  

        return prefix


    """
    Función que añade la etiqueta texto a otra etiqueta padre
    """
    def addText(self,padre, text):

        etiquetaText = ET.SubElement(padre, "text")
        etiquetaText.text = str(text)


    """
    Función que añade algunas marcas opcionales de moodleXML con valores por defecto
    """
    def defaultMarks(self,question ,generalfb_val="", defaultgrade_val="1.0000000", penalty_val="0.0000000", hidden_val="0"):

        gf = ET.SubElement(question, "generalfeedback", format="html")
        self.addText(gf,generalfb_val)

        defaultgrade = ET.SubElement(question, "defaultgrade")
        defaultgrade.text = defaultgrade_val

        penalty = ET.SubElement(question, "penalty")
        penalty.text = penalty_val


        hidden = ET.SubElement(question, "hidden")
        hidden.text = hidden_val


    """
    Función que añade las marcas de retroalimentación
    """
    def feedbackMarks(self,question,textcorrect="", textpartially="", textincorrect=""):

        correctfeedback = ET.SubElement(question, "correctfeedback", format="html")
        self.addText(correctfeedback, textcorrect)
        

        partiallycorrectfeedback = ET.SubElement(question, "partiallycorrectfeedback", format="html")
        self.addText(partiallycorrectfeedback, textpartially)

        incorrectfeedback = ET.SubElement(question, "incorrectfeedback", format="html")
        self.addText(incorrectfeedback, textincorrect)



    """
    Función que crea una pregunta Verdadero/Falso en formato MoodleXML
    """
    def produceTFQuestion(self,question,tag, questionParse ,choices, correctChoiceID,point,score):


        #Creamos el contenido de la pregunta
        name = ET.SubElement(question, "name")    
        self.addText(name,str(tag.attrib["title"]))

        questiontext = ET.SubElement(question, "questiontext", format="html")
        self.addText(questiontext,str(questionParse))
    
        #Creamos atributos/elementos correspondientes a la pregunta
        generalfeedback = ""
        defaultgrade = str(point)
        penalty="1"
        hidden="0"
        self.defaultMarks(question,generalfeedback, defaultgrade, penalty, hidden)
        itemfeed = []
        for meta in tag.getchildren():
            if str(meta.attrib) != "{}":
                itemfeed.append(meta.flow_mat.material.mattext)
        
        if len(itemfeed)==1:
            itemfeed.append(meta.flow_mat.material.mattext)

        if len(itemfeed)==0:
            itemfeed.append("")
   

        #Creamos las respuestas 
        for choice in choices:
            choiceID = str(choice.attrib['ident']).strip()
            answer = ET.SubElement(question, "answer", fraction="", format="moodle_auto_format")

            if str(choice.material.mattext) == "Verdadero":
                text = "true"
            else:
                text="false"

            self.addText(answer, text)

            awfeedback = ET.SubElement(answer, "feedback",format="html")
            awfeedbacktext = ET.SubElement(awfeedback, "text")

            print(itemfeed)
            if len(itemfeed)>1:
                awfeedbacktext.text = str(itemfeed[1])
            else:
                awfeedbacktext.text = str(itemfeed[0])

            if choiceID == correctChoiceID[0]:
                answer.set('fraction', score)
                awfeedbacktext.text = str(itemfeed[0])
            else:
                answer.set('fraction', '0')  




    """
    Función que crea una pregunta 'Múltiple elección' 
    o 'Múltiple respuesta' en formato MoodleXML.
    """
    def produceMCQuestion(self,question,tag, questionParse ,choices, correctChoiceID, point,score):

        #Creamos el contenido de la pregunta
        name = ET.SubElement(question, "name")
        self.addText(name, str(tag.attrib["title"]))

        questiontext = ET.SubElement(question, "questiontext", format="html")
        self.addText(questiontext, str(questionParse))
    
        #Creamos atributos/elementos correspondientes a la pregunta
        generalfeedback = ""
        defaultgrade = str(point)
        self.defaultMarks(question, generalfeedback, defaultgrade)

        single = ET.SubElement(question, "single")
        if tag.presentation.response_lid.attrib['rcardinality'] == 'Single':
            single.text = "true"
        else:
            single.text = "false"    

        shuffleanswers = ET.SubElement(question, "shuffleanswers")
        shuffleanswers.text = "true"

        answernumbering = ET.SubElement(question, "answernumbering")
        answernumbering.text = "abc"
    
        #### Feed Back ###
        if len(correctChoiceID)>1:
            correct = " <p>Respuesta correcta</p>"
            parcial = " <p>Respuesta parcialmente correcta.</p> "
            incorrect = " <p>Respuesta incorrecta.</p> "
            self.feedbackMarks(question, correct, parcial, incorrect)
        elif (len(tag.getchildren())>3):#Cuando la pregunta tiene etiquetas retroalimentación (ademas de los tres bloques principales)
            itemfeedback =  tag.findall('./{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}itemfeedback')
            for feed in itemfeedback:
                if feed.attrib['ident'] == "correct_fb":
                    correct = feed.flow_mat.material.mattext
                elif (feed.attrib['ident'] == "general_incorrect_fb"):
                    incorrect = feed.flow_mat.material.mattext

            self.feedbackMarks(question, correct, "", incorrect)

        else:#Cuando no hay etiquetas de retroalimentación
            self.feedbackMarks(question)
        #################


        #Creamos las respuestas 
        scoreMax = score
        for choice in choices:
            choiceID = str(choice.attrib['ident']).strip() 

            answer = ET.SubElement(question, "answer", fraction="", format="html")
            self.addText(answer, str(choice.material.mattext) )
        
            awfeedback = ET.SubElement(answer, "feedback",format="html")
            awfeedbacktext = ET.SubElement(awfeedback, "text")
            awfeedbacktext.text = ""

            if len(correctChoiceID)>1: #MultiRespuesta
                score = str(float(scoreMax)/len(correctChoiceID))

                for correct in correctChoiceID:
                    
                    if choiceID == str(correct):
                        answer.set('fraction', score)
                        awfeedbacktext.text = ""
                        break
                    else:
                        answer.set('fraction', '0')  
            else:    
                if choiceID == correctChoiceID[0]:
                    answer.set('fraction', score)
                    awfeedbacktext.text = ""
                else:
                    answer.set('fraction', '0')
    


    """
    Función que crea una pregunta Respuesta corta en formato MoodleXML.
    """
    def produceSAQuestion(self,question,tag, questionParse ,choices, point,score):
        
        #Creamos el contenido de la pregunta
        name = ET.SubElement(question, "name")
        self.addText(name, str(tag.attrib["title"]))
        
        questiontext = ET.SubElement(question, "questiontext", format="html")
        self.addText(questiontext, str(questionParse))    

        #Creamos atributos/elementos correspondientes a la pregunta
        generalfeedback = "Las respuestas correctas son " + str(choices)
        defaultgrade = str(point)
        self.defaultMarks(question, generalfeedback, defaultgrade)
        usecase = ET.SubElement(question, "usecase")
        usecase.text = "0"

        #Creamos las respuestas 
        for choice in choices:

            answer = ET.SubElement(question, "answer", fraction=score, format="moodle_auto_format")
            self.addText(answer, choice)
        
            awfeedback = ET.SubElement(answer, "feedback",format="html")
            awfeedbacktext = ET.SubElement(awfeedback, "text")
            awfeedbacktext.text = ""


    """
    Función que crea una pregunta Respuesta numérica en formato MoodleXML.
    """
    def produceNUMQuestion(self,question,tag, questionParse ,choices,tolerancias, point,scores,tipoUnidades):

        #Creamos el contenido de la pregunta
        name = ET.SubElement(question, "name")
        self.addText(name, str(tag.attrib["title"]))
        
        questiontext = ET.SubElement(question, "questiontext", format="html")
        self.addText(questiontext, str(questionParse))   
        
        #Creamos atributos/elementos correspondientes a la pregunta
        self.defaultMarks(question, "", str(point))

        #Creamos las respuestas 
        for i in range( len(choices)):

            answer = ET.SubElement(question, "answer", fraction=scores[i], format="moodle_auto_format")
            self.addText(answer, choices[i])
        
            awfeedback = ET.SubElement(answer, "feedback",format="html")
            awfeedbacktext = ET.SubElement(awfeedback, "text")
            awfeedbacktext.text = ""

            tolerance = ET.SubElement(answer,"tolerance")
            tolerance.text = str(tolerancias[i])


        ####Creamos marcas que añaden más información a la pregunta con valores por defecto

        #Cómo se introducen las unidades (0 input, 1 radio, 2 select)
        unitgradingtype = ET.SubElement(question, "unitgradingtype")
        if tipoUnidades == "Decimal":
            unitgradingtype.text = "0"

        #Penalización por unidad incorrecta
        unitpenalty = ET.SubElement(question, "unitpenalty")
        unitpenalty.text="0.1"

        #Calificación de unidades (3 none, 1 graded, 0 optional)
        showunits = ET.SubElement(question, "showunits")
        showunits.text="3"

        #En qué posición se ponen las unidades
        unitsleft = ET.SubElement(question, "unitsleft")
        unitsleft.text = "0"


    """
    Función que crea una pregunta Empajeramiento en formato MoodleXML.
    """
    def produceMATCHQuestion(self,question,tag, questionParse , subquestions ,choices,point):

        #Creamos el contenido de la pregunta
        name = ET.SubElement(question, "name")
        self.addText(name, str(tag.attrib["title"]))

        questiontext = ET.SubElement(question, "questiontext", format="html")
        self.addText(questiontext, str(questionParse))    

        #Creamos atributos/elementos correspondientes a la pregunta
        generalfeedback = ""
        defaultgrade = str(point)
        self.defaultMarks(question, generalfeedback, defaultgrade)
        shuffleanswers = ET.SubElement(question, "shuffleanswers")
        shuffleanswers.text = "true"
        correct = " <p>Respuesta correcta</p>"
        parcial = " <p>Respuesta parcialmente correcta.</p> "
        incorrect = " <p>Respuesta incorrecta.</p> "
        self.feedbackMarks(question, correct, parcial, incorrect)

        #Creamos las respuestas 
        for i in range(len(subquestions)):
            #Columna izquierda
            subquestion = ET.SubElement(question, "subquestion", format="html")
            self.addText(subquestion,subquestions[i])

            #Columna derecha
            ansSub = ET.SubElement(subquestion, "answer")
            self.addText(ansSub,choices[i])


    """
    Función que añade al fichero de salida las marcas de un fichero XML y la estructura del arbol.
    """
    def writequestionfile(self,quiz, filename):
        

        f = open(filename, "w")
        f.write('<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>')
        try:
            f.write(ET.tostring(quiz, encoding='utf-8', method='xml').decode('utf-8'))
        except Exception as e:
            error_message = f'Error al añadir el arbol al fichero. Technical details:\n\t{e}'
            print(error_message)
            print("\n")
            return -1        
        
        print(f"Wrote {filename}")


    """
    Función que añade algunas marcas HTML para una mejor presentación
    """
    def fixHtmlText(self,text):
        
        text = urllib.parse.unquote(str(text))
    
        text = re.sub('</div>','</p></div> </div></prompt></div> ',text)
        text = re.sub('<div>',' <div><prompt><div> <div><p> ',text)

        return text


    """
    Función que convierte el fichero QTI.
    """
    def convertQTI(self,inputfile, outputfolder):
        
        if not os.path.exists(outputfolder): os.makedirs(outputfolder)
        val = self.readQTI(inputfile, outputfolder)
        #shutil.make_archive(outputfolder, 'zip', outputfolder)
        return val


    """
    Función principal, con la que la interfaz se comunicará 
    """
    def m_conv(self):
        
        inputfile = self.file_input
        outputfolder = self.path_out+'/ExportMOODLE_XML'
       
        print(f'Input file is "{inputfile}"')
        print(f'Output FOLDER is "{outputfolder}"')
        try:
            val = self.convertQTI(inputfile, outputfolder)
            if val==0:
                return 0
            if val==-1:
                return -1
        except:
            print("An exception occurred in convertQTI")
            return -1
        else:
            return 1