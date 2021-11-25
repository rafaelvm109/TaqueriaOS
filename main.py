import json
import time
import datetime
import boto3

# json + queue de prueba
with open('TACOS/data.json') as f:
  data = json.load(f)

queue = []

for i in range(len(data)):
    queue.append(data[i])


# AWS STUFF
sqs = boto3.client("sqs")
queue_url = "https://sqs.us-east-1.amazonaws.com/292274580527/sqs_cc106_team_2"

# numero de mensajes aproximado en el queue
def get_number_messages():
    queue_attr = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=["ApproximateNumberOfMessages"]
    )
    return int(queue_attr["Attributes"]["ApproximateNumberOfMessages"])

# lee el mensaje xd, me falta probarlo para entender mejor como funciona
def read_message():
    response = sqs.receive_message(QueueUrl=queue_url)
    message = response["messages"]
    orden = json.loads(message[0]["Body"])
    print("Atendiendo orden: {0}. Leyebdi mensaje del queue. Tiempo pendiente {1}".format(orden["request_id"], orden["tiempo_pendiente"]))
    return message[0], orden

# borra el mensaje agregando el tiempo en caso de que se haya concluido o lo regresa al queue / no me acuerdo que era lo de receiptHandle
def delete_message(message, orden, complete):
    if complete:
        orden["end_datetime"] = str(datetime.now().timestamp())
        print("Orden {0} Terminado. Mensaje borrado del queue.".format(orden["request_id"]))
        print(orden)
    else:
        print("Orden {0} Pendiente. Regresando mensaje al queue. tiempo pendiente{1}".format(orden["request_id"], orden["tiempo_pendiente"]))
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=message["ReceiptHandle"]
    )

# creo que borra el mensaje y lo vuelve a reescribir en el queue
def write_message(mensaje, orden):
    delete_message(mensaje, orden, False)
    response = sqs.send_message(
        QueueUrl = queue_url,
        MessageBody = (json.dumps(orden))
    )

# agregar y modificar el round robin 

# CONSTANTES
FILLINGS = ["salsa", "guacamole", "cilantro", "cebolla"]
MAX_FILLINGS = {"salsa": 150, "guacamole": 100, "cilantro": 200, "cebolla": 200, "tortillas": 50}
REFILL_TIME = {"salsa": 15, "guacamole": 20, "cilantro": 10, "cebolla": 10, "tortillas": 5}
MEAT_TYPES = ["tripa", "cabeza", "asada", "suadero", "adobada"]


# CLASES
class Taquero():
    def __init__(self, name, carnes):
        self.name = name
        self.carnes = carnes
        self.tortillas = 50
        self.quesadillas = 5
        self.fillings = MAX_FILLINGS
        self.rest = 0 # 1000 tacos -> 30 segundos de descanso
        self.fan = 0 # 600 tacos -> prender ventilador por 60


    def resting(self, sleep_time):
        if self.rest == 1000:
            time.sleep(sleep_time)
        # si el queue esta vacio tambien puede descansar

    def fan_on(self):
        self.fan = True
    
    def fan_off(self):
        self.fan = False

    # funcion para que el taquero reciba una orden del queue
    def process_order(self):
        pass

    # funcion para que el taquero pueda prepara un taco tomando en cuenta el tiempo de preparo de cada ingrediente
    # 1s por taco + 0.5s por ingrediente
    def make_taco(self):
        # Hacer taco y agregar ingredientes, al terminar un taco, se cambia el contador y se reinicia el estado del taco
        # Si se acaba el tiempo, se guarda el estado del taco y el numero de tacos
        # Idea: guardar estado y tacos restantes en el json
        pass

    # revisa las ordenes del queue principal (basado en el tipo de carne del taquero) y las agrega a su queue especifico
    # parametros: carnes = lista con las carnes que maneja el taquero, id = id de la ultima orden revisada por el taquero
    def get_orders(self, carnes, id):
        ordenes_revisadas = 0
        while True:
            # Agregar orden al queue del taquero
            for i in data["orden"]:
                if i["meat"] in carnes and i["status"] == "open" and len(queue_taquero) < 5:
                    queue_taquero.append(i)
            
            id += 1
            # Si el taquero ya reviso muchas ordenes y ya tiene algo en su queue, se detendra para que continue haciendo tacos
            # y no este perdiendo el tiempo
            if ordenes_revisadas == 50 and len(queue) > 0:
                return id + 1
                
            # Si el taquero ya tiene 5 ordenes en su queue o termino de revisar todas las ordenes, tambien se detendra.
            if len(queue) == 5 or len(queue_principal) == id:
                return id



# esta persona se encarga de hacer quesadillas y mandarlas a los taqueros, idealmente nunca deja de hacer quesadillas
# si todos los taqueros tienen 5 quesadillas, la personas va a poner las extras en un stack de quesadillas (que nunca se enfrian :O)
class Quesadillas():
    def __init__(self, name):
        self.name = name
        # otros atributos???

    # 20s por quesadilla
    def preparar_quesadillas():
        pass


# es possible que sea mejor hacerlo como una funcion y no como clase
class Chalan():
    def __init__(self, name, taquero1, taquero2):
        self.name = name
        self.taqueros = [taquero1, taquero2] # lista de taqueros del chalan
        self.ingredientes = {"salsa": 0, "guacamole": 0, "cilantro": 0, "cebolla": 0, "tortillas": 0}

    # # checar los fillings de un taquero en especifico
    # # pensando mejor no va a ser necesario, asumiendo que el chalan sigue un ciclo infinito para rellenar
    # def checar_fillings(self, taquero):
    #     pass

    # rellenar los fillings de un taquero en especifico
    # tiempos = {"cilantro":10, "cebolla":10, "salsa":15, "guacamole":20, "tortillas":5}
    # aplicar el ciclo infinito para que el chalan nunca deje de trabajar
    def rellenar_fillings(self):
        pass


'''
Otras cosas:

- funcion para asignar ordenes a los taqueros como un mesero +/- ???
- 
'''
