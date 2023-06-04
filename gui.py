#!/usr/bin/env python

import os
import pathlib
import shutil
import time
import tkinter as tk
from tkinter import ttk
from tkinter import PhotoImage
import tkinter.filedialog
import webbrowser
from tkinter import filedialog
from pathlib import Path
import utils.QTI2moodle as qti
import utils.moodle2QTI as moodle
from base64 import b64decode
from tkinter import messagebox as mb

"""
Interfaz del sistema
"""

"""
Obtiene los iconos almacenados en el fichero "imagenes.txt"
"""
def leerIconos(fichero_icono):
    
    datos = []
    with open(fichero_icono) as fname:
        lineas = fname.readlines()
        for linea in lineas:
            datos.append(linea.strip('\n'))

    return datos

"""
Modal que enseña un mensaje de información sobre los tipos de cuestionarios que puede convertir
"""
def informacion():
        mb.showinfo(
            "Información"
            ,"Tipos de cuestionarios que soporta:\n\t-Multielección\n\t-True/False\n\t-Empajeramiento\n\t-Númerica\n\t-Respuesta Corta"
            ,
            )


"""
Función principal que se ejecuta y enseña la interfaz
"""
def main():
    
    file_name = ''

    #Ventana principal
    window = tk.Tk()
    #Definimos ciertos valores de la ventana
    window.title('CONVERSOR LMS')
    window.columnconfigure(0, weight=1)
    window.rowconfigure(0, weight=1)
    window.config(width=400, height=300, bg='white')
    window.resizable(width=False, height=False)
    #window.eval('tk::PlaceWindow . center') #En el caso que queramos centrarla en la pantalla

    #Creacion de botones y elementos

    ###############
    run_button = tk.Button(window,text= "CONVERTIR")
    run_message_label = tk.Label(
            window,
            text='\nInforme de ejecución:\n',
            bg = "#1E89BF",
            fg= "white",
            relief='ridge',
            width=50,
            height=1,
        )
    run_message_frame = tk.Frame(
        window,width=50, height=25,    
        borderwidth=1, relief='sunken', bg='white',
    )
    run_message_text = tk.Text(run_message_frame,height=4, width=50)
    ###############


    current_row = 0

    iconos=leerIconos("iconos/imagenes.txt")#Obtenemos las imagenes que se usaran en la interfaz
    icono = PhotoImage(data=b64decode(iconos[0]))
    info = PhotoImage(data=b64decode(iconos[5]))
    
    #--------------------
    header_label_icono_1 = tk.Label(window,image=icono)
    header_label_icono_1.grid(
        row=current_row,column=0,columnspan=1,padx=(15,0),pady=10
    )
    header_label_icono_1['bg']="white"

    #--------------------
    header_label = tk.Label(
        window,
        text='Conversor de Cuestionarios entre \nMoodleXML & QTI/IMS de CANVAS',
        font=(None, 16),
    )

    header_label.config( 
        bg= "white", 
        fg= "#1E89BF"
    )

    header_label.grid(
        row=current_row, column=1, columnspan=1, padx=5,pady=10,
        sticky='nsew',
    )
    #--------------------


    header_label_icono_2 = tk.Label(
        window,
        image=icono
    )
    header_label_icono_2['bg']="white"
    header_label_icono_2.grid(
        row=current_row, column=2,columnspan=1,padx=(0,15)
    )

    #--------------------

    # current_row += 1
    # header_link_label = tk.Label(
    #     window,
    #     text='github.com/gpoore/text2qti',
    #     font=(None, 14), fg='blue', cursor='hand2',
    # )
    # header_link_label.bind('<Button-1>', lambda x: webbrowser.open_new('https://github.com/DiegoHiguita/ConversorLMS_TFG.git'))
    # header_link_label.grid(
    #     row=current_row, column=1, columnspan=1, padx=(30, 30),
    #     sticky='nsew',
    # )

    current_row += 1
    version_label = tk.Label(
        window,
        text=f'Version 1.0',
        bg="white"
    )

    version_label.grid(
        row=current_row, column=1, columnspan=1, padx=(30, 30), pady=(0, 30),
        sticky='nsew',
    )
    current_row += 1

    last_dir = None

    #Función que permite navegar por las carpetas del dispositivo
    def browse_files():
        nonlocal file_name
        nonlocal last_dir
        if last_dir is None:
            initialdir = pathlib.Path('~').expanduser()
        else:
            initialdir = last_dir
        file_name = tkinter.filedialog.askopenfilename(
            initialdir=initialdir,
            filetypes=(
                ("Archivos de xml", "*.xml"),
                ("Todos los archivos", "*.*")
            )
        )
        if file_name:
            if last_dir is None:
                last_dir = pathlib.Path(file_name).parent
            file_browser_button.config(text=f'"{pathlib.Path(file_name).stem}"', fg="white", bg="#72D673", activebackground="#67BF67")            
            run()
        else:
            file_browser_button.config(text=f'Seleccione el cuestionario', fg="white", bg="#F5745D", activebackground="#DC4F36")
            run_button.grid_remove()
            run_message_frame.grid_remove()
            run_message_label.grid_remove()



    file_browser_button = tk.Button(
        window,
        text='Seleccione el cuestionario',
        fg="white",
        bg="#F5745D",
        command=browse_files,
        activebackground="#DC4F36",
        activeforeground="white"
    )
    file_browser_button.grid(
        row=current_row, column=1, columnspan=1, padx=(5, 5), pady=(5, 0),
        sticky='nsew',
    )

    current_row += 1

    infoButton = tk.Button(
        window,
        image=info,
        bg="white",
        command=informacion
    )

    infoButton.grid(
        row=current_row, column=1, columnspan=1, padx=200, pady=(5,15),
        sticky='nsew',
    )

    current_row += 1

    #----------------------
    moodle_ico = PhotoImage(data=b64decode(iconos[1]))
    canvas_ico = PhotoImage(data=b64decode(iconos[2]))
    flecha = PhotoImage(data=b64decode(iconos[3]))
    cambio = PhotoImage(data=b64decode(iconos[4]))


    flecha_label = tk.Label(
        window,
        image=flecha
    )
    flecha_label['bg']="white"
    flecha_label.grid(
        row=current_row, column=1,columnspan=1,padx=(0,0),
        sticky='nsew',
    )


    tipo1_label = tk.Label(
        window,
        image=canvas_ico
    )
    tipo1_label['bg']="white"
    tipo1_label.grid(
        row=current_row, column=1,columnspan=1,padx=(25,0),
        sticky='w',
    )

    tipo2_label = tk.Label(
        window,
        image=moodle_ico
    )
    tipo2_label['bg']="white"
    tipo2_label.grid(
        row=current_row, column=1,columnspan=1,padx=(0,15),
        sticky='e',
    )

    current_row += 1
    
    tipo1_label_text = tk.Label(
        window,
        text="Canvas QTI/IMS",
        bg="white",
        fg="#1E89BF"
    )
    
    tipo1_label_text.grid(
        row=current_row, column=1,columnspan=1,
        sticky='w',
    )

    tipo2_label_text = tk.Label(
        window,
        text="MoodleXML",
        bg="white",
        fg="#1E89BF"
    )
    
    tipo2_label_text.grid(
        row=current_row, column=1,columnspan=1,
        sticky='e',
    )


    current_row += 1

    #Función que permite establecer cual será el formato de inicio y cual será el formato fin
    def changeType():
        auxLabel=tk.Label(
            image=tipo1_label['image'],
            text=tipo1_label_text['text']
        )

        if tipo2_label_text['text']=='MoodleXML': 
            tipo1_label.grid(
                padx=(15,0)
            )
            tipo2_label.grid(
                padx=(0,25)
            )
        else: 
            tipo1_label.grid(
                padx=(25,0)
            )
            tipo2_label.grid(
                padx=(0,15)
            )   

        tipo1_label.config(
            image=tipo2_label['image'] 
        )

        tipo1_label_text.config(
            text=tipo2_label_text['text']
        )

        tipo2_label.config(
            image=auxLabel['image']
        )
        
        tipo2_label_text.config(
            text=auxLabel['text']
        )

        
    
    #-----------------------

    change_button = tk.Button(
        window,
        image=cambio,
        command=changeType,
        bg="white"
    )
   
    change_button.grid(
        row=current_row, column=1,padx=150, pady=15,
        sticky='nsew',
    )
    
    #-------------------------
    current_row += 2
    
    #Función que expande la ventana principal para poder permitir la ejecución
    def run():

        run_button.grid(
            row=current_row,column=0,columnspan=4 ,padx=30, pady=10
        )
        run_button.config(
            command=convertir,
            bg="#4BBD4B", activebackground="#3FA63F", 
            fg= "white"
        )

        
        run_message_label.grid(
            row=current_row+1, column=1, columnspan=1, padx=(30, 30), pady=(0, 0),
            sticky='nsew',
        )
            
        run_message_frame.grid(
            row=current_row+2, column=1, columnspan=1, padx=30, pady=(0, 20),
            sticky='nsew',
        )

        
        run_message_text['state']=tk.NORMAL
        run_message_text.delete(1.0, tk.END)
        run_message_text.config(
            fg="gray"
        )
        run_message_text.insert(tk.INSERT, "Esperando...")
        run_message_text['state']=tk.DISABLED
        run_message_text.grid()
        run_message_text['state']=tk.DISABLED

        
    #Función que llama a la clase correspondiente para realizar la conversión
    def convertir():

        run_message_text['state']=tk.NORMAL
        
        error_message = None
        file_path = pathlib.Path(file_name)
        if tipo1_label_text["text"] == "Canvas QTI/IMS":
            qti_2moodle = qti.QTI2moodle(file_name, file_path.stem, file_path.parent.as_posix())
            conv=qti_2moodle.m_conv()
            if conv==-1:
                error_message = f'Quiz creation failed'
            elif conv==0:
                error_message = f'No questions to convert'
 
        else:
            moodle_2qti = moodle.moodle2QTI(file_name, file_path.stem, file_path.parent.as_posix())
            conv=moodle_2qti.m_conv()
            if conv==-1:
                error_message = f'Quiz creation failed'
            elif conv==0:
                error_message = f'No questions to convert'  

        
        if error_message:
            
            run_message_text.delete(1.0, tk.END)
            run_message_text.insert(tk.INSERT, error_message)
            run_message_text['fg'] = 'red'
        else:
            run_message_text.delete(1.0, tk.END)
            run_message_text.insert(tk.INSERT, f'Created quiz "{file_path.parent.as_posix()}/ExportMOODLE_XML.zip"')
            run_message_text['fg'] = 'green'
        
        
        run_message_text['state']=tk.DISABLED
    

    window.iconphoto(True, icono)
    window.mainloop()


if __name__ == "__main__":
    main()