"""
About version: Programa ejecutable que incluye IA Generativa + Conexión SSH + Conexión SQL + Envío de Email
"""

import os                                                   # Librería que permite acceder al sistema operativo
import sys                                                  # Librería que permite acceder al sistema operativo
from netmiko import ConnectHandler                          # Librería conexión SSH
import mysql.connector                                      # Librería conexión SQL
from decouple import Config, RepositoryEnv                  # Librería para variables de entorno
from email.message import EmailMessage                      # Librería para enviar correos
import smtplib                                              # Librería para enviar correos
import ssl                                                  # Librería para añadir seguridad a correos
import itertools                                            # Librería para la animación de progreso
import time                                                 # Librería para manejo de tiempo                
from datetime import datetime, timedelta                    # Librería para manejo de fechas
from langchain_ollama import OllamaEmbeddings, ChatOllama   # Librería IA

    
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
    
def imprimir_banner():
    """Imprime el banner del programa con el título y descripción."""
    banner = """
    ██████╗ ███████╗███╗   ███╗ ██████╗      █████╗ ██╗      █████╗ ██████╗ ███╗   ███╗ █████╗ ███████╗    ██╗████████╗
    ██╔══██╗██╔════╝████╗ ████║██╔═══██╗    ██╔══██╗██║     ██╔══██╗██╔══██╗████╗ ████║██╔══██╗██╔════╝    ██║╚══██╔══╝
    ██║  ██║█████╗  ██╔████╔██║██║   ██║    ███████║██║     ███████║██████╔╝██╔████╔██║███████║███████╗    ██║   ██║   
    ██║  ██║██╔══╝  ██║╚██╔╝██║██║   ██║    ██╔══██║██║     ██╔══██║██╔══██╗██║╚██╔╝██║██╔══██║╚════██║    ██║   ██║   
    ██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝    ██║  ██║███████╗██║  ██║██║  ██║██║ ╚═╝ ██║██║  ██║███████║    ██║   ██║   
    ╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝    ╚═╝   ╚═╝   
    """
    print("="*110)
    print(banner)
    print("\nPowered by Google Gemma 2\n")
    print("="*110 + "\n")

def salir_programa():
        """Cierra el programa."""
        print("\nCerrando programa...")
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
            host=config("MYSQL_HOST"),          # IP o nombre de host del servidor MySQL
            port=config("MYSQL_PORT"),          # Puerto de conexión MySQL
            database=config("MYSQL_DB"),        # Nombre de la base de datos
            user=config("MYSQL_USER"),          # Nombre de usuario de MySQL
            password=config("MYSQL_PASS")       # Contraseña del usuario de MySQL
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
    comandos = [f"amos {sitio}", "lt all", "alt"]      
    
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
            if cmd=="alt" :
                amos = sitio + ">\n" + output[:-15]
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
        content = """
        DEMO ALARMAS IT
        
        Sitios con alarmas críticas activas:
        
        """
        for w in warning:
            content += w
            
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
        
def consulta_sitios_it(lista_it):
    """Invoca la IA generativa y consulta mediante comandos SSH los sitios IT."""
    barra = BarraProgreso(len(lista_it))
    
    llm = ChatOllama(model="gemma2", temperature=0)
    system_prompt = """
    Eres una IA diseñada para monitorear alarmas críticas en sitios móviles de una red de telecomunicaciones.
    Tu función principal es recibir un log de alarmas extraído de un sitio móvil y analizarlo en busca de alarmas críticas.
    Las alarmas se clasifican en crítica, mayor, menor y de advertencia, las cuales se abrevian C, M, m, w respectivamente.
    Los nombres de los sitios móviles son siempre 3 letras mayúsculas y 3 números, por ejemplo: UVA123, MOM999, NRE987.
    Si detectas una o más alarmas críticas activas en el log, responde con el mensaje: "Alerta! Nombre_sitio: Nombre_alarmas".
    Si no encuentras alarmas críticas, no generes una respuesta.
    Sigue estrictamente este formato de respuesta, y prioriza la precisión en la detección de alarmas críticas.
    """
    mensajes = [("system", system_prompt), ("human", "")]
    
    zero_time = time.time()
    
    for sitio in lista_it:
        barra.actualizar(f"| Analizando sitio {sitio}.")
        amos = conexion_ssh(sitio)

        if amos is not None:
            mensajes[1] = ("human", amos)
            respuesta = llm.invoke(mensajes)
            
            if "Alerta!" in respuesta.content:
                warning.append(respuesta.content[8:])

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
