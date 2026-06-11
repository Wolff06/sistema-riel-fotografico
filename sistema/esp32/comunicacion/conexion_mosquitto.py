
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

    def establecer_conexion_mqtt(self,callback=None):
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
        if callback:
           self.cliente.set_callback(callback)
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
    
    def publicar(self, topico, mensaje, retain=False, qos=0):
        """
        Publica un mensaje en el tópico indicado.
        """
        if self.conectado and self.cliente:
            self.cliente.publish(topico, mensaje, retain=retain, qos=qos)

    def suscribir(self, topico):
        """
        Se suscribe a un tópico para recibir mensajes.
        """
        if self.conectado and self.cliente:
            self.cliente.subscribe(topico)
    
    def esperar_mensajes(self):
        """
        Bloquea hasta recibir un mensaje (usa el callback definido).
        """
        if self.conectado and self.cliente:
            self.cliente.wait_msg()
    
    def checar_mensajes(self):
        """
        No bloquea: revisa si hay mensajes pendientes.
        """
        if self.conectado and self.cliente:
            self.cliente.check_msg()



