import json
from time import sleep
import datetime
import boto3
import threading

# json + queue de prueba
with open('1203-TACOS/data.json') as f:
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
    print("Atendiendo orden: {0}. Leyendo mensaje del queue. Tiempo pendiente {1}".format(orden["request_id"], orden["tiempo_pendiente"]))
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
MAX_FILLINGS = {"salsa": 150, "guacamole": 100, "cilantro": 200, "cebolla": 200, "tortillas": 50, "quesadillas": 5}
REFILL_TIME = {"salsa": 15, "guacamole": 20, "cilantro": 10, "cebolla": 10, "tortillas": 5}
MEAT_TYPES = ["tripa", "cabeza", "asada", "suadero", "adobada"]


# CLASES
class Taquero():
    def __init__(self, name, carnes):
        self.name = name
        self.carnes = carnes
        self.fillings = MAX_FILLINGS
        self.rest = 0 # 1000 tacos -> 30 segundos de descanso
        self.fan = 0 # 600 tacos -> prender ventilador por 60
        self.queue_taquero = [] # queue individual taquero


    def resting(self, sleep_time):
        if self.rest == 1000:
            print(f"Taquero {self.name} empezó su descanso")
            sleep(sleep_time)
            print(f"Taquero {self.name} terminó su descanso")
        # si el queue esta vacio tambien puede descansar

    def fan_control(self):
        if self.fan is True:
            self.fan = False
            print(f"se apagó el ventilador del taquero {self.name}")
        else:
            self.fan = True
            print(f"se prendió el ventilador del taquero {self.name}")

    # funcion para que el taquero pueda prepara un taco tomando en cuenta el tiempo de preparo de cada ingrediente
    # 1s por taco + 0.5s por ingrediente
    # parametros: num = numero de la ordenes que se va a enfocar de las ordenes del queue del taquero
    def make_taco(self, num):
        # Hacer taco y agregar ingredientes, al terminar un taco, se cambia el contador y se reinicia el estado del taco
        # Si se acaba el tiempo, se guarda el estado del taco y el numero de tacos
        order = self.queue_taquero[num]
        taco_state = order["taco_state"]
        size = len(order["ingredients"])
        tipo = "quesadillas"
        time = 0
        finish = False

        if order["type"] == "taco":
            tipo = "tortillas"

        print("Taquero {0} inicio con la orden {1}".format(self.name, order["part_id"])
        )
        while time < 5:
            # Poner la tortilla
            if taco_state == 0 and self.fillings[tipo] > 0:
                if time == 4.5:
                    sleep(0.5)
                    time += 0.5
                    taco_state += 0.5
                    print("Taquero {0} preparo media tortilla de la orden {1}".format(self.name, order["part_id"]))
                else:
                    sleep(1)
                    time += 1
                    taco_state += 1
                    self.fillings[tipo] -= 1
                    print("Taquero {0} preparo una tortilla de la orden {1}".format(self.name, order["part_id"]))
            
            # Poner media tortilla
            elif taco_state == 0.5 and self.fillings[tipo] > 0:
                sleep(0.5)
                time += 0.5
                taco_state += 0.5
                self.fillings[tipo] -= 1
                print("Taquero {0} agrego la otra media tortilla de la orden {1}".format(self.name, order["part_id"]))

            # Poner un ingrediente
            elif taco_state >= 1 and size > 0 and self.fillings[order["ingredients"][int(taco_state) - 2]] > 0:
                sleep(0.5)
                time += 0.5
                taco_state += 1
                self.fillings[order["ingredients"][int(taco_state) - 2]] -= 1
                print("Taquero {0} agrego {1} a la orden {2}".format(self.name, order["ingredients"][int(taco_state) - 2], order["part_id"]))

            else:
                break

            # Revisar si ya esta hecho el taco
            if taco_state == size + 1:
                taco_state = 0
                order["complete_tacos"] += 1
                print("Taquero {0} termino un taco de la orden {1}".format(self.name, order["part_id"]))

                if order["complete_tacos"] == order["quantity"]:
                    order["status"] = "complete"
                    # Quitar orden del queue
                    print("Taquero {0} termino de preparar la orden {1}".format(self.name, order["part_id"]))
                    # A G R E G A R
                    # Al terminar la orden, revisar si todas las otras partes de la orden estan completas
                    # Hacerlo con una funcion
                    self.queue_taquero.pop(num)
                    finish = True
                    return finish
                    break
        
        if finish is False:
            order["taco_state"] = taco_state
            print("Taquero {0} paso a la siguiente orden {1}".format(self.name, order["part_id"]))
            return finish


    # revisa las ordenes del queue principal (basado en el tipo de carne del taquero) y las agrega a su queue especifico
    # parametros: carnes = lista con las carnes que maneja el taquero, id = id de la ultima orden revisada por el taquero
    def get_orders(self, id):
        # Si el taquero ya tiene 5 ordenes en su queue o termino de revisar todas las ordenes, tambien se detendra.
        while len(self.queue_taquero) < 5 or len(queue) < id:
            order = queue[id]["orden"]

            for i in order:
                # Agregar orden al queue del taquero
                if i["meat"] in self.carnes and i["status"] == "open" and len(self.queue_taquero) < 5:
                    i["status"] = "taken"
                    self.queue_taquero.append(i)
                    # Agregar las variables
                    i["taco_state"] = 0
                    i["complete_tacos"] = 0
                    print("Se agrego la orden {0} del taquero {1}".format(i["part_id"], self.name))


            id += 1

        return id - 1



# esta persona se encarga de hacer quesadillas y mandarlas a los taqueros, idealmente nunca deja de hacer quesadillas
# si todos los taqueros tienen 5 quesadillas, la personas va a poner las extras en un stack de quesadillas (que nunca se enfrian :O)
class Quesadillas():
    def __init__(self, name):
        self.name = name
        self.quesadillas = 0

    # 20s por quesadilla
    def preparar_quesadillas(self):
        print(f"Quesadillera {self.name} esta preparando una quesadilla")
        sleep(20)
        self.quesadillas += 1
        print(f"Quesadillera {self.name} termino una quesadilla")


    # Para que de quesadillas a los taqueros
    def dar_quesadilla(self, taquero):
        if taquero.fillings["quesadillas"] < 5 and self.quesadillas > 0:
            taquero.fillings["quesadillas"] += 1
            self.quesadillas -= 1
            print(f"Quesadillera {self.name} le dio una quesadilla a {taquero.name}")


class Chalan():
    def __init__(self, name, taquero1, taquero2):
        self.name = name
        self.taqueros = [taquero1, taquero2] # lista de taqueros del chalan
        self.ingredientes = {"salsa": 0, "guacamole": 0, "cilantro": 0, "cebolla": 0, "tortillas": 0}

    # rellenar los fillings de un taquero en especifico
    # tiempos = {"cilantro":10, "cebolla":10, "salsa":15, "guacamole":20, "tortillas":5}
    # aplicar el ciclo infinito para que el chalan nunca deje de trabajar
    def rellenar_fillings(self, num):
        pos = 0
        tiempo = 0

        while pos < 5:
            self.ingredientes[pos] = MAX_FILLINGS[pos] - self.taqueros[num].fillings[pos]
            tiempo += (self.ingredientes[pos] * REFILL_TIME[pos]) / MAX_FILLINGS[pos]
            pos += 1

        print(f"Chalan {self.name} esta rellenando los ingredientes del taquero {self.taqueros[num].name}")
        sleep(tiempo)

        pos = 0
        while pos < 5:
            self.taqueros[num].fillings[pos] += self.ingredientes[pos]
            print(f"Chalan {self.name} relleno al taquero {self.taqueros[num].name} los siguientes ingredientes: {self.ingredientes}")
            pos += 1



# -------------------------------------------------------------------

t1 = Taquero('Kench', ['tripa', 'cabeza'])
t2 = Taquero('Zac', ['asada', 'suadero'])
t3 = Taquero('Tahm', ['asada', 'suadero'])
t4 = Taquero('Maokai', ['adobada'])

def init():
    id = 0
    num = 0
    finish = True
    
    while(True):
        if finish is True:
            id = t1.get_orders(id)
            finish = False
        
        finish = t1.make_taco(num)

        num += 1
        if num >= len(t1.queue_taquero):
            num = 0

        # Sigue agregar chalan como thread




init()
