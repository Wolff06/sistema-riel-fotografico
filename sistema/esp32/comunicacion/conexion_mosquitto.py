
import ubinascii
from umqtt.simple import MQTTClient

class MQTTLink:

    def __init__(self, servidor, puerto, usuario="", contrasena=""):
        self.servidor = servidor
        self.puerto = puerto
        self.usuario = usuario
        self.contrasena = contrasena
        self.id = ubinascii.hexlify(machine.unique_id())
        self.conectado = False
        self.cliente = None

    def establecer_conexion_mqtt(self):
        """
        Parámetros: ninguno.
        Acción:     Cierra cualquier sesión MQTT previa y abre una nueva
                    conexión con el broker configurado.
        Retorna:    None.
        """
        self.cerrar_conexion_mqtt()
        self.cliente = MQTTClient(
            self.id,
            self.servidor,
            self.puerto,
            self.usuario,
            self.contrasena,
            keepalive=60    
        )
        self.cliente.connect()
        self.conectado = True

    def cerrar_conexion_mqtt(self):
        """
        Parámetros: ninguno.
        Acción:     Desconecta al cliente MQTT si hay una sesión activa
                    y actualiza la bandera de estado.
        Retorna:    None.
        """
        if self.cliente is not None:
            self.cliente.disconnect()
        self.conectado = False
