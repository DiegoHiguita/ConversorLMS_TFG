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
import uuid



answerindex = 999  #Variable global para asignar números ID a las respuestas


"""
Clase para leer/convertir aquellos ficheros
que tienen una estructura en formato MoodleXML, y través de las equivalencias 
crea el fichero en formato QTI/IMS.
"""
class moodle2QTI():


    """
    Inicializar los atributos de los objetos pertenecientes a la clase moodle2QTI
    """
    def __init__(self, file_input, out, path_out):
        
        self.file_input = file_input #Fichero de entrada
        self.out = out #Nombre del fichero de salida
        self.path_out = path_out #Ruta que almacenará el fichero de salida



    """
    Función que lee el fichero de entrada en formato MoodleXML, y a través de las equivalencias 
    y las siguientes funciones de la clase, crea el fichero de salida en formato QTI/IMS.
    """
    def readMoodle(self,inputfile, outputfolder):
        
        #Obtenemos el arbol xml de MoodleXML
        try:
            tree = ET.parse(inputfile)
        except Exception as e:
            error_message = f'An error occurred in reading the quiz file. Technical details:\n\t{e}'
            print(error_message)


        root = tree.getroot()


        #Obtenemos todas las preguntas del cuestionario 
        preguntas = root.findall("question")


        if len(preguntas)==0:
            print("No hay prgeuntas para convertir")
            return 0

        #Variables de control
        have_cat=0
        name=""

        #Creamos el arbol correspondiente al fichero de salida en formato QTI
        ET.register_namespace('', "http://www.imsglobal.org/xsd/ims_qtiasiv1p2")  # no ns0 namespaces here
        
        questestinterop = ET.fromstring(str(
            '<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.imsglobal.org/xsd/ims_qtiasiv1p2 http://www.imsglobal.org/xsd/ims_qtiasiv1p2p1.xsd"></questestinterop>'))
        

        u = uuid.uuid1() #Identificadores unicos   
        ident = u.hex

        #Creamos los metadatos por defecto para cualquier cuestonario
        assessment = ET.SubElement(questestinterop,"assessment", ident=str(ident), title="")
        qtimetadata = ET.SubElement(assessment, "qtimetadata")
        qtimetadatafield = ET.SubElement(qtimetadata, "qtimetadatafield")
        fieldlabel = ET.SubElement(qtimetadatafield,"fieldlabel")
        fieldlabel.text = "cc_maxattempts"
        fieldentry = ET.SubElement(qtimetadatafield,"fieldentry")
        fieldentry.text = "1"    

        #Creamos la seccion que almacenará las preguntas
        section = ET.SubElement(assessment,"section", ident="root_section")
        convertix = 0  # Ennumeracion de preguntas a convertir

        #Recorremos los items(preguntas) del cuestionario 
        for q in preguntas:    
            
            try:
                if q.attrib['type'] == "category":
                    #En el caso que el fichero MoodleXML tenga categoria, podremos extraer un titulo para el cuestionario
                    text = q.find('category/text').text
                    name = self.foundName(text)  
                    assessment.set('title',name)
                    have_cat=1 #Indicamos que se ha encontrado la categoria
                else:
                    if have_cat==0:
                        #En el caso que no contenga categoria, usaremos como titulo el nombre del fichero de entrada
                        text = self.file_input
                        name = str(ident)
                        assessment.set('title',text)

                
                if q.attrib['type'] != "category":  #Corresponde con aquellas preguntas reales que no son categoria
                    
                    #Obtenemos valores para los metadatos
                    qtype = q.attrib['type']
                    u = uuid.uuid1()
                    convertix = convertix + 1
                    #Obtenemos el prefijo correspondiente para el nombre del fichero de salida
                    prefix = self.getprefix(qtype)
                    q.set('convertix', prefix + str(convertix))
                    item = ET.SubElement(section,"item",ident=q.get('convertix'), title="")
                    title = q.find('name/text').text
                    item.set('title', title)

                    #Procedemos a convertir la pregunta dependiendo de su tipo

                    if qtype == 'shortanswer':
                        q.set('type',"short_answer_question")                
                    
                        self.produceSAQuestion(q, item, u)
                    #--------------------------------------------------------

                    if qtype == 'multichoice':
                        q.set('type',"multiple_choice_question")

                        if q.find('single').text == "false":
                            q.set('type',"multiple_answers_question")
                        
                        self.produceMCQuestion(q, item, u)
                    #--------------------------------------------------------

                    if qtype == 'truefalse':
                        q.set('type',"true_false_question")              
                        self.produceTFQuestion(q,item,u)
                    #--------------------------------------------------------

                    if qtype == 'matching':
                        q.set('type',"matching_question")              
                        self.produceMATCHQuestion(q,item,u)  
                    #--------------------------------------------------------
                        
                    if qtype == 'numerical':
                        q.set('type',"numerical_question")              
                        self.produceNUMQuestion(q,item,u) 
            except e:
                print("Error in produce: ", qtype)
                print("Details: ", e)
                return -1      


        #Creamos el fichero de salida    
        outputfolder = outputfolder+'/'+name
        out = prefix+name+'.xml'
        filename = outputfolder+'/'+ out

        try:
            if not os.path.exists(outputfolder):
                os.makedirs(outputfolder)
                
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        
        self.writequestionfile(questestinterop, filename)

        return 1,outputfolder


    """
    Función que busca el nombre del cuestionario 
    """
    def foundName(self,text):
        if 'para' in text:
            posicion = text.index('para')+4
        elif 'en' in text:
            posicion = text.index('en')+2
        else:    
            posicion = 0

        text = text[posicion+1:len(text)]    
        text = re.sub('\.', '', text)  
        
        print(posicion)

        if posicion!=0 and '/' in text:
            posicion = text.index('/')
            text = text[posicion+1:len(text)]  

        if posicion==0: #EN el caso de que no encuentre un patron y podamos sacar el nombre, le añadimos un identificador unico
            u = uuid.uuid1()  
            ident = u.hex
            text=str(ident)

        return text


    """
    Función que obtiene un prefijo según el tipo de pregunta
    """
    def getprefix(self,qtype):
        prefix = 'AAA_ERROR'
        if qtype == 'shortanswer':
            prefix = 'MSHORT_'
        if qtype == 'numerical':
            prefix = 'NUMERIC_'
        if qtype == 'matching':
            prefix = 'MATCH_'
        if qtype == 'multichoice':
            prefix = "MULTI_"
        if qtype == 'truefalse':
            prefix = "TRUEFALSE_"    
        return prefix


    """
    Función que crea los tres bloques que contiene todos los items de QTI
    """
    def createBlocksItem(self,item):
        itemmetadata = ET.SubElement(item, "itemmetadata")
        presentation = ET.SubElement(item, "presentation")
        resprocessing = ET.SubElement(item, "resprocessing")

        return itemmetadata,presentation,resprocessing


    """
    Función que crea los metadatos correspondientes a un item
    """
    def createItemmetadata(self,tag,itemmetadata,u):
        possible_answer = tag.findall('answer')

        #generar id de respuestas
        original_answer_ids = self.generatedIds(possible_answer)
        
        question_type = tag.attrib['type']
        point_possible = tag.find('defaultgrade').text
        
        assessment_question_identifierref = u.hex

        v_fieldlabel = ['question_type','points_possible','original_answer_ids','assessment_question_identifierref']
        v_fieldentry = [question_type,point_possible,original_answer_ids,assessment_question_identifierref]
        
        qtimetadata = ET.SubElement(itemmetadata, "qtimetadata")
        
        for i in range(len(v_fieldlabel)):
            qtimetadatafield = ET.SubElement(qtimetadata, "qtimetadatafield")

            fieldlabel = ET.SubElement(qtimetadatafield,"fieldlabel")
            fieldlabel.text = v_fieldlabel[i]

            fieldentry = ET.SubElement(qtimetadatafield,"fieldentry")
            fieldentry.text = v_fieldentry[i]

        return possible_answer,original_answer_ids


    """
    Función que crea identificadores para las respuestas
    """
    def generatedIds(self,possible_answer):

        global answerindex 

        original_answer_ids = ""
        for i in range(len(possible_answer)):
            original_answer_ids += str(answerindex)
            if i==len(possible_answer)-1:
                original_answer_ids += ""
            else:
                original_answer_ids +="," 

            answerindex += 1


        return original_answer_ids  


    """
    Función que crea la etiqueta <material> que almacena las cadenas de texto
    """
    def makeMaterial(self,padre,text,texttype="text/html"):
        material = ET.SubElement(padre, "material")
        
        mattext = ET.SubElement(material,"mattext", texttype=texttype)
        mattext.text = text

    """
    Función que crea la etiqueta <outcomes> 
    """
    def makeOutcomes(self,padre):
        outcomes = ET.SubElement(padre,"outcomes")
        decvar = ET.SubElement(outcomes, "decvar", maxvalue="100", minvalue="0",varname="SCORE", vartype="Decimal")
        

    """
    Función que crea una pregunta Múltiple elección o
    Múltiple respuesta en formato QTI/IMS.
    """
    def produceMCQuestion(self,tag, item, u):
        
        #Creamos los bloques de la pregunta
        itemmetadata,presentation,resprocessing = self.createBlocksItem(item)

 
        #### ITEMMETADATA -> Creamos los metadatos de la pregunta
        possible_answer,original_answer_ids=self.createItemmetadata(tag,itemmetadata,u)


        #### PRESENTATION -> Creamos la visualización de la pregunta
        m_qtext = tag.find('questiontext/text').text  
        self.makeMaterial(presentation,m_qtext,"text/html")#Contenido de la pregunta

        #atributos/elementos correspondientes a la pregunta
        identRes = "response1"
        response_lid = ET.SubElement(presentation,"response_lid", ident=identRes, rcardinality="")
        if tag.find('single').text == 'true':
            response_lid.set('rcardinality', 'Single')
        else:    
            response_lid.set('rcardinality', 'Multiple')

        render_choice = ET.SubElement(response_lid, "render_choice")  
        
        #Creamos las respuestas 
        original_answer_ids = original_answer_ids.split(',')
        i=0
        correctlist = []
        badlist =[]
        scores = []
        for ans in possible_answer:   

            atext = ans.find('text').text
            response_label = ET.SubElement(render_choice,"response_label",ident=original_answer_ids[i])
            self.makeMaterial(response_label,atext,"text/html")

            if int(float(ans.attrib['fraction'])) > 10:  #Aquellas que tengan menos puntaje no se consideran respuestas correctas
                correctlist.append(original_answer_ids[i])
                scores.append(int(float(ans.attrib['fraction'])))
            else:
                badlist.append(original_answer_ids[i])
            i+=1

        ####

        #### RESPROCESSING -> Creamos el procesamiento de la pregunta
        self.makeOutcomes(resprocessing)
        
        respcondition = ET.SubElement(resprocessing, "respcondition", {'continue':"No"})
        conditionvar = ET.SubElement(respcondition,"conditionvar")

        if correctlist==1: # Multiple opción con una sola respuesta
            varequal = ET.SubElement(conditionvar,"varequal",respident=identRes)
            varequal.text = correctlist[0]
            
        else: #Multiple opción con multiple respuesta
            eti_and = ET.SubElement(conditionvar, "and")   
            for correctId in correctlist:
                varequal = ET.SubElement(eti_and,"varequal",respident=identRes)
                varequal.text = correctId
            
            for badId in badlist:
                eti_not = ET.SubElement(eti_and,"not")
                varequal = ET.SubElement(eti_not,"varequal",respident=identRes)
                varequal.text = badId   
                
        
        setvar = ET.SubElement(respcondition,"setvar",action="Set",varname="SCORE")
        setvar.text = "100"     


    """
    Función que crea una pregunta  Verdadero/Falso en formato QTI/IMS.
    """
    def produceTFQuestion(self,tag, item, u):

        #Creamos los bloques de la pregunta
        itemmetadata,presentation,resprocessing = self.createBlocksItem(item)

        #### ITEMMETADATA -> Creamos los metadatos de la pregunta
        possible_answer,original_answer_ids=self.createItemmetadata(tag,itemmetadata,u)

        #### PRESENTATION -> Creamos la visualización de la pregunta
        m_qtext = tag.find('questiontext/text').text  #Contenido de la pregunta
        self.makeMaterial(presentation,m_qtext,"text/html")

        #atributos/elementos correspondientes a la pregunta
        identRes = "response1"
        response_lid = ET.SubElement(presentation,"response_lid", ident=identRes, rcardinality="")
        response_lid.set('rcardinality', 'Single')
        render_choice = ET.SubElement(response_lid, "render_choice")  
        
        #Creamos las respuestas 
        original_answer_ids = original_answer_ids.split(',')
        i=0
    
        for ans in possible_answer:   

            atext = ans.find('text').text
            if atext=="true":
                atext="Verdadero"
            elif atext=="false":
                atext="Falso"  

            response_label = ET.SubElement(render_choice,"response_label",ident=original_answer_ids[i])
            self.makeMaterial(response_label,atext,"text/html")

            if int(float(ans.attrib['fraction'])) > 10: #Aquellas que tengan menos puntaje no se consideran respuestas correctas
                original_answer_ids.append(original_answer_ids[i])

            itemfeedback = ET.SubElement(item,"itemfeedback",ident=original_answer_ids[i]+"_fb")
            flow_mat = ET.SubElement(itemfeedback,"flow_mat")
            fd = ans.find('feedback/text').text
            self.makeMaterial(flow_mat,fd,"text/html")

            i+=1
        ###

        #### RESPROCESSING -> Creamos el procesamiento de la pregunta
        
        self.makeOutcomes(resprocessing)

        for i in range(len(possible_answer)+1):

            if i < len(possible_answer):
                respcondition = ET.SubElement(resprocessing, "respcondition", {'continue':'Yes'})
            else:
                respcondition = ET.SubElement(resprocessing, "respcondition", {'continue':'No'})

            conditionvar = ET.SubElement(respcondition,"conditionvar")
            varequal = ET.SubElement(conditionvar,"varequal",respident=identRes)
            varequal.text = original_answer_ids[i]
                
            if i < len(possible_answer):
                displayfeedback = ET.SubElement(respcondition,"displayfeedback",feedbacktype="Response", linkrefid=original_answer_ids[i]+"_fb")
            else:
                setvar = ET.SubElement(respcondition,"setvar",action="Set",varname="SCORE")
                setvar.text ="100"

            

    """
    Función que crea una pregunta Respuesta corta en formato QTI/IMS.
    """
    def produceSAQuestion(self,tag, item, u):

        #Creamos los bloques de la pregunta
        itemmetadata,presentation,resprocessing = self.createBlocksItem(item)

        #### ITEMMETADATA -> Creamos los metadatos de la pregunta
        possible_answer,original_answer_ids=self.createItemmetadata(tag,itemmetadata,u)

        #### PRESENTATION -> Creamos la visualización de la pregunta
        m_qtext = tag.find('questiontext/text').text  #Contenido de la pregunta
        self.makeMaterial(presentation,m_qtext,"text/html")

        #atributos/elementos correspondientes a la pregunta
        identRes = "response1"
        response_str = ET.SubElement(presentation,"response_str", ident=identRes, rcardinality="Single")

        render_fib = ET.SubElement(response_str, "render_fib")  
        response_label = ET.SubElement(render_fib,"response_label", ident="answer1", rshuffle="No")
        ###
     
        #### RESPROCESSING -> Creamos el procesamiento de la pregunta
        original_answer_ids = original_answer_ids.split(',')

        self.makeOutcomes(resprocessing)

        respcondition = ET.SubElement(resprocessing, "respcondition", {'continue':'No'})
        conditionvar = ET.SubElement(respcondition,"conditionvar")

        #Creamos las respuestas 
        for ans in possible_answer:
            varequal = ET.SubElement(conditionvar,"varequal", respident="response1")
            atext = ans.find('text').text
            varequal.text = atext
        
        setvar = ET.SubElement(respcondition,"setvar",action="Set",varname="SCORE")
        setvar.text ="100"    


    """
    Función que crea una pregunta Respuesta numérica en formato QTI/IMS.
    """
    def produceNUMQuestion(self,tag,item,u):
        
        #Creamos los bloques de la pregunta
        itemmetadata,presentation,resprocessing = self.createBlocksItem(item)

        #### ITEMMETADATA -> Creamos los metadatos de la pregunta
        possible_answer,original_answer_ids=self.createItemmetadata(tag,itemmetadata,u)

        #### PRESENTATION -> Creamos la visualización de la pregunta
        m_qtext = tag.find('questiontext/text').text  #Contenido de la pregunta      
        self.makeMaterial(presentation,m_qtext)

        #atributos/elementos correspondientes a la pregunta
        identRes = "response1"
        response_str = ET.SubElement(presentation,"response_str", ident=identRes, rcardinality="Single")
        render_fib = ET.SubElement(response_str, "render_fib", fibtype="Decimal")  
        response_label = ET.SubElement(render_fib,"response_label", ident="answer1")
        ###

        #### RESPROCESSING -> Creamos el procesamiento de la pregunta
        self.makeOutcomes(resprocessing)

        for ans in possible_answer: #Creamos las respuestas 
            tolerancia = ans.find('tolerance').text
            valor = ans.find('text').text
            score = ans.attrib['fraction']
            respcondition = ET.SubElement(resprocessing,"respcondition", {'continue':'No'})
            conditionvar = ET.SubElement(respcondition,"conditionvar")
            et_or = ET.SubElement(conditionvar,"or")

            varequal = ET.SubElement(et_or,"varequal",respident=identRes) #valor exacto
            varequal.text = valor

            et_and = ET.SubElement(et_or,"and") #Error aceptado
            vargte = ET.SubElement(et_and,"vargte",respident=identRes)
            vargte.text = str(round(float(valor) - float(tolerancia),5))
            varlte = ET.SubElement(et_and,"varlte",respident=identRes)
            varlte.text = str(round(float(valor) + float(tolerancia),5))

            setvar = ET.SubElement(respcondition,"setvar",action="Set",varname="SCORE")
            setvar.text = str(score)



    """
    Función que crea una pregunta Empajeramiento en formato QTI/IMS.
    """
    def produceMATCHQuestion(self,tag, item, u):

        #Creamos los bloques de la pregunta
        itemmetadata,presentation,resprocessing = self.createBlocksItem(item)

        #### ITEMMETADATA -> Creamos los metadatos de la pregunta        
        
        subquestion = tag.findall('subquestion')
        possible_answer = tag.findall('subquestion/answer')
        #en un principio se deberia mantener la relacion/orden subquestion-answer que viene de moodle

        subquestion_ids = self.generatedIds(subquestion) #generar id de subquestions
        original_answer_ids = self.generatedIds(possible_answer)  #generar id de respuestas

        question_type = tag.attrib['type']
        point_possible = tag.find('defaultgrade').text
        
        assessment_question_identifierref = u.hex

        v_fieldlabel = ['question_type','points_possible','original_answer_ids','assessment_question_identifierref']
        v_fieldentry = [question_type,point_possible,original_answer_ids,assessment_question_identifierref]
        qtimetadata = ET.SubElement(itemmetadata, "qtimetadata")
        for i in range(len(v_fieldlabel)):
            qtimetadatafield = ET.SubElement(qtimetadata, "qtimetadatafield")

            fieldlabel = ET.SubElement(qtimetadatafield,"fieldlabel")
            fieldlabel.text = v_fieldlabel[i]

            fieldentry = ET.SubElement(qtimetadatafield,"fieldentry")
            fieldentry.text = v_fieldentry[i]
        ###

        #### PRESENTATION -> Creamos la visualización de la pregunta
        m_qtext = tag.find('questiontext/text').text  #Contenido de la pregunta      
        self.makeMaterial(presentation,m_qtext,"text/html")

        #Creamos las respuestas 
        original_answer_ids = original_answer_ids.split(',') 
        subquestion_ids = subquestion_ids.split(',')
        i=0

        for sub in subquestion: #Columna izquierda
            identRes = "response_"+original_answer_ids[i]
            response_lid = ET.SubElement(presentation,"response_lid", ident=identRes)

            subText = sub.find('text').text
            self.makeMaterial(response_lid,subText,"text/html")

            render_choice = ET.SubElement(response_lid, "render_choice")  

            j=0
            for ans in possible_answer: #Columna derecha
                #su atributo shuffle indica si hay que reordenar aleatoriamente los ítems
                response_label = ET.SubElement(render_choice,"response_label", ident=subquestion_ids[j])
                ansText = ans.find('text').text
                self.makeMaterial(response_label,ansText,"text/html")
                j+=1

            i+=1
        ###

        #### RESPROCESSING -> Creamos el procesamiento de la pregunta
        self.makeOutcomes(resprocessing)
        subScores = float(100/len(possible_answer))
        i=0
        for ans in possible_answer:
            respcondition = ET.SubElement(resprocessing, "respcondition")
            conditionvar = ET.SubElement(respcondition,"conditionvar")
            varequal = ET.SubElement(conditionvar,"varequal", respident="response_"+original_answer_ids[i])
            varequal.text = str(subquestion_ids[i])
            setvar = ET.SubElement(respcondition,"setvar",action="Add",varname="SCORE")
            setvar.text = str(subScores)
            i+=1


    """
    Función que añade al fichero de salida las marcas de un fichero XML y la estructura del arbol.
    """
    def writequestionfile(self,questestinterop, filename):
        f = open(filename, "w")
        f.write('<?xml version="1.0" encoding="utf-8" standalone="yes"?>')
        try:
            f.write(ET.tostring(questestinterop, encoding='utf-8', method='xml').decode('utf-8'))
        except Exception as e:
            error_message = f'Error al añadir el arbol al fichero. Technical details:\n\t{e}'
            print(error_message)
            print("\n")
            return -1

        print(f"Wrote {filename}")


    """
    Función que convierte el fichero MoodleXML.
    """
    def convertMoodle(self,inputfile, outputfolder):
        val,outputfolder=self.readMoodle(inputfile, outputfolder)
        shutil.make_archive(outputfolder, 'zip', outputfolder) #El formato QTI se debe subir a canvas comprimido en .zip
        return val
    

    """
    Función principal, con la que la interfaz se comunicará 
    """
    def m_conv(self):
        
        inputfile = self.file_input
        outputfolder = self.path_out+'/ExportQTI'
       
        print(f'Input file is "{inputfile}"')
        print(f'Output FOLDER is "{outputfolder}"')
        
        try:
            val = self.convertMoodle(inputfile, outputfolder)
            if val==0:
                return 0
            if val==-1:
                return -1
        except:
            print("An exception occurred in convertMoodle")
            return -1
        else:
            return 1