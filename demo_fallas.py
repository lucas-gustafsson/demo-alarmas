"""
About version: Programa ejecutable que incluye IA Generativa + RAG + Conexión SSH + Conexión SQL + Envío de Email
"""

import os                                                   # Librería que permite acceder al sistema operativo
import sys                                                  # Librería que permite acceder al sistema operativo
from pathlib import Path                                    # Librería que permite acceder al PATH        
from netmiko import ConnectHandler                          # Librería conexión SSH
import mysql.connector                                      # Librería conexión SQL
from decouple import Config, RepositoryEnv                  # Librería para variables de entorno
from email.message import EmailMessage                      # Librería para enviar correos
import smtplib                                              # Librería para enviar correos
import ssl                                                  # Librería para añadir seguridad a correos
import itertools                                            # Librería para la animación de progreso
import time                                                 # Librería para manejo de tiempo                
from datetime import datetime, timedelta                    # Librería para manejo de fechas
from langchain_ollama import OllamaEmbeddings, ChatOllama   # Librerías IA
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

class BarraProgreso:
    """Barra de progreso visible para el usuario."""
    def __init__(self, total_sitios):
        self.total_sitios = total_sitios
        self.sitio_actual = 0

    def actualizar(self, mensaje=""):
        self.sitio_actual += 1
        porcentaje = (self.sitio_actual / self.total_sitios) * 100
        barra_largo = 20  
        completado = int(barra_largo * self.sitio_actual / self.total_sitios)
        barra = f"[{'#' * completado}{'-' * (barra_largo - completado)}]"
        estado = f"\rProgreso: {self.sitio_actual}/{self.total_sitios} {barra} {porcentaje:.1f}% {mensaje}"
        sys.stdout.write(estado)
        sys.stdout.flush()
        time.sleep(0.1)

    def completado(self):
        sys.stdout.write("\n\n¡Análisis completado!\n")
        sys.stdout.flush()

def limpiar_pantalla():
    """Limpia la pantalla de la consola."""
    os.system('cls' if os.name == 'nt' else 'clear')

def limpiar_texto(texto):
    """Divide en líneas, elimina espacios de cada línea y une las líneas con un salto de línea."""
    lineas = texto.splitlines()
    lineas_limpias = [linea.strip() for linea in lineas if linea.strip()]
    texto_limpio = '\n'.join(lineas_limpias)
    return texto_limpio
    
def imprimir_banner():
    """Imprime el banner del programa con el título y descripción."""
    banner = """
    ██████╗ ███████╗███╗   ███╗ ██████╗     ███████╗ █████╗ ██╗     ██╗      █████╗ ███████╗    ██╗████████╗
    ██╔══██╗██╔════╝████╗ ████║██╔═══██╗    ██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔════╝    ██║╚══██╔══╝
    ██║  ██║█████╗  ██╔████╔██║██║   ██║    ███████╗███████║██║     ██║     ███████║███████╗    ██║   ██║   
    ██║  ██║██╔══╝  ██║╚██╔╝██║██║   ██║    ██╔════╝██╔══██║██║     ██║     ██╔══██║╚════██║    ██║   ██║   
    ██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝    ██║     ██║  ██║███████╗███████╗██║  ██║███████║    ██║   ██║   
    ╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝    ╚═╝   ╚═╝   
    """
    print("="*110)
    print(banner)
    print("\nPowered by Google Gemma 2")
    print("\nBETA Alarmas y Sincronismo\n")
    print("="*110 + "\n")

def salir_programa():
        """Cierra el programa."""
        print("\n\nCerrando programa...")
        time.sleep(1)
        sys.exit(0)
        
def check_credenciales():
    """Comprueba las credenciales y VPN."""
    # Conexion SQL
    try:
        connection = mysql.connector.connect(
            host=config("MYSQL_HOST"),
            port=config("MYSQL_PORT"),
            database=config("MYSQL_DB"),
            user=config("MYSQL_USER"),
            password=config("MYSQL_PASS")
        )
        connection.close()
    
    except Exception as e:
        print(f"\nError de conexión con servidor MySQL: {str(e)}")
        salir_programa()
        
    # Conexion SSH
    try:
        connection = ConnectHandler(
            device_type="linux",
            host=config("ENM_HOST"),
            port=config("ENM_PORT"),
            username=config("ENM_USER"),
            password=config("ENM_PASS"),
        )
        connection.disconnect()
    
    except Exception as e:
        print(f"\nError de conexión con servidor ENM: {str(e)}")
        salir_programa()

def obtener_lista_it():
    """Solicita rango de días para el análisis y consulta el servidor RASP para obtener la lista de sitios IT."""
    while True:
        try:
            dias = int(input("\nIngrese el rango de días para el análisis: "))
            if dias <= 0:
                print("\nPor favor, ingrese un número válido.")
                continue
                            
            print(f"\nPeriodo de análisis: {dias} dias.")
            lista_it = conexion_sql(dias)
            print(f"\nSitios a analizar: {len(lista_it)}.")
            
            confirmacion = input("\n¿Desea continuar? (yes/no): ").lower()
            if confirmacion in ['yes', 'y']:
                return lista_it
            elif confirmacion in ['no', 'n']:
                print("\nPor favor, ingrese el rango de días nuevamente.")
            else:
                print("\nPor favor, responda 'yes' o 'no'.")
        
        except KeyboardInterrupt:
            salir_programa()
            
        except:
            print("\nPor favor, ingrese un número válido.")
            
def conexion_sql(dias):
    """Realiza la conexión con el servidor SQL donde se obtiene la lista de sitios IT."""
    fechas = [(datetime.today() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(dias)]
    fechas_str = "'" + "', '".join(fechas) + "'"
    
    try:
        lista_it=[]
        # Establecer la conexión a la base de datos
        connection = mysql.connector.connect(
            host=config("MYSQL_HOST"),
            port=config("MYSQL_PORT"),
            database=config("MYSQL_DB"),
            user=config("MYSQL_USER"),
            password=config("MYSQL_PASS")
        )

        if connection.is_connected():
            time.sleep(0.5)
            cursor = connection.cursor()
            cursor.execute(f"""SELECT SITIO
                            FROM SITIOS
                            WHERE ESTADO IN ('INITIAL_TUNNING', 'INITIAL_TUNNING_PARCIAL')
                            AND FECHA_INTEGRACION IN ({fechas_str});""")
            for (sitio_it,) in cursor:
                lista_it.append(sitio_it)           
            cursor.close()
            connection.close()
        return lista_it    
    
    except Exception as e:
        print(f"\nError de conexión con servidor MySQL:\n{str(e)}")
        salir_programa()

def conexion_ssh(sitio):
    """Función que permite la conexión SSH a ENM."""
    comandos = [f"amos {sitio}", "lt all", "alt", "sts", "st cell"]      
    amos = ""
    try:
        connection = ConnectHandler(
            device_type="linux",
            host=config("ENM_HOST"),
            port=config("ENM_PORT"),
            username=config("ENM_USER"),
            password=config("ENM_PASS"),
        )
        
        for cmd in comandos:
            output = connection.send_command(cmd, expect_string=f"{sitio}>", read_timeout=30, strip_command=True, strip_prompt=True)
            if cmd=="alt" or cmd=="sts" or cmd=="st cell":
                amos += sitio + ">\n" + output[:-15] + "\n"
        connection.disconnect()
        return amos
        
    except:
        return None

def conexion_mail(warning):
    """
    Conexión a Gmail y envío de Warning.
    """
    user = config("MAIL_USER")
    password = config("MAIL_PASS")
    team = config("MAIL_TEAM").split(",")
    subject = f"​⚠️ WARNING! {datetime.today().strftime("%Y-%m-%d")}"
    
    if len(warning) > 0:
        content = "DEMO FALLAS IT" + "\n\n"
        for w in warning:
            content += w + "\n"
            
        em = EmailMessage()
        em["From"] = user
        em["To"] = team
        em["Subject"] = subject
        em.set_content(content)
        
        context = ssl.create_default_context()      # Añadir SSL (extra de seguridad)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(user, password)
            smtp.send_message(em)
        return None
    
    else:
        return None

def cargar_vectorstore():
    """
    Función que carga o crea la base vectorial
    """
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
    
    try:
        documentos = []
        for archivo in Path("RAG").glob("*.txt"):
            with archivo.open('r', encoding='utf-8') as file:
                contenido = file.read()
                documento = Document(page_content=contenido, metadata={"source": archivo.name})
                documentos.append(documento)
        
        vectorstore = InMemoryVectorStore.from_documents(documentos, embedding=embeddings)
        print("\nRAG cargado con éxito.\n")
        return vectorstore
    
    except Exception as e:
        print("\nError cargando RAG. Se debe agregar documentos a la carpeta RAG.")
        print(str(e))
        salir_programa()
        
def cargar_rag():
    """
    Función que inicia el RAG
    """
    llm = ChatOllama(model="gemma2:9b-instruct-q8_0", temperature=0)
    
    vectorstore = cargar_vectorstore()
    
    retriever = vectorstore.as_retriever(search_kwargs={'k': 1})
    
    template = """
    Eres una IA diseñada para monitorear logs de sitios móviles de una red de telecomunicaciones.
    Tu función principal es recibir un log extraído de un sitio móvil y detectar las fallas en él.
    En primer lugar añade a la respuesta: "Sitio: nombre_sitio".
    Si detectas una o más alarmas activas de tipo Crítica (C) añade a la respuesta "Falla Alarma Crítica Activa: nombre_alarmas".
    Si detectas que el sitio no está sincronizado añade a la respuesta "Falla de Sincronismo".
    Si detectas que una o más celdas están deshabilitadas añade a la respuesta "Falla Celdas Deshabilitadas: nombre_celdas"
    Si no detectas fallas añade a la respuesta: "Todo en orden".
    Sigue estrictamente este formato de respuesta.

    Usa las siguientes piezas de contexto para responder la pregunta al final.

    {context}

    Question: {question}

    Helpful Answer:
    """

    custom_rag_prompt = PromptTemplate.from_template(template)
                    
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | custom_rag_prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain
        
def consulta_sitios_it(lista_it):
    """Invoca la IA generativa y consulta mediante comandos SSH los sitios IT."""   
    rag = cargar_rag()
    barra = BarraProgreso(len(lista_it))

    warning=[]
    zero_time = time.time()
    
    for sitio in lista_it:
        barra.actualizar(f"| Analizando sitio {sitio}.")
        amos = conexion_ssh(sitio)
        
        if amos is not None:
            respuesta = rag.invoke(amos)
            if "Falla" in respuesta:
                respuesta_limpia = limpiar_texto(respuesta)
                warning.append(respuesta_limpia)

    barra.completado()             
    end_time = time.time() - zero_time            
    print(f"\nTiempo total de ejecución: {round(end_time/60)} minutos.")
    return warning

def main():
    """
    MAIN
    """
    #limpiar_pantalla()
    imprimir_banner()
    check_credenciales()
    lista_it = obtener_lista_it()
    
    print("\nIniciando análisis de sitios...")
    
    warning = consulta_sitios_it(lista_it)
    conexion_mail(warning)
    
if __name__ == "__main__":
    config = Config(RepositoryEnv('config.env'))
    main()
