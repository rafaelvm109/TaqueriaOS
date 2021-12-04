import json
from time import sleep
import time
from datetime import datetime
import boto3
import threading
import logging

# logging
logging.basicConfig(filename='logs.log', format='%(asctime)s %(message)s', filemode='w', datefmt='%m/%d/%Y %H:%M:%S', encoding='utf-8', level=logging.DEBUG)

# json + queue de prueba
# C A M B I A R
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
        self.fillings = {"salsa": 150, "guacamole": 100, "cilantro": 200, "cebolla": 200, "tortillas": 50, "quesadillas": 5}
        self.rest = 0 # 1000 tacos -> 30 segundos de descanso
        self.fan = 0 # 600 tacos -> prender ventilador por 60
        self.fan_on = False
        self.queue_taquero = [] # queue individual taquero

    def resting(self):
        print(f"Taquero {self.name} empezó su descanso")
        logging.info(f"Taquero {self.name} empezó su descanso")
        sleep(30)
        print(f"Taquero {self.name} terminó su descanso")
        logging.info(f"Taquero {self.name} terminó su descanso")
        # si el queue esta vacio tambien puede descansar

    def fan_control(self):
        self.fan_on = True
        print(f"se prendió el ventilador del taquero {self.name}")
        logging.info("se prendió el ventilador del taquero {self.name}")
        sleep(60)
        self.fan_on = False
        print(f"se apagó el ventilador del taquero {self.name}")
        logging.info(f"se apagó el ventilador del taquero {self.name}")

    # funcion para que el taquero pueda prepara un taco tomando en cuenta el tiempo de preparo de cada ingrediente
    # 1s por taco + 0.5s por ingrediente
    # parametros: num = numero de la ordenes que se va a enfocar de las ordenes del queue del taquero
    def make_taco(self):
        num = 0
        id = 0
        finish = True

        while True:
            if finish is True:
                id = self.get_orders(id)
                finish = False

            if len(self.queue_taquero) > 0:
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

                print("Taquero {0} inicio con la orden {1}".format(self.name, order["part_id"]))
                logging.info("Taquero {0} inicio con la orden {1}".format(self.name, order["part_id"]))
                while time < 5:
                    # Poner la tortilla
                    if taco_state == 0 and self.fillings[tipo] > 0:
                        if time == 4.5:
                            sleep(0.5)
                            time += 0.5
                            taco_state += 0.5
                            print("Taquero {0} preparo media tortilla de la orden {1}".format(self.name, order["part_id"]))
                            logging.info("Taquero {0} preparo media tortilla de la orden {1}".format(self.name, order["part_id"]))
                        else:
                            sleep(1)
                            time += 1
                            taco_state += 1
                            self.fillings[tipo] -= 1
                            print("Taquero {0} preparo una tortilla de la orden {1}".format(self.name, order["part_id"]))
                            logging.info("Taquero {0} preparo una tortilla de la orden {1}".format(self.name, order["part_id"]))
                    
                    # Poner media tortilla
                    elif taco_state == 0.5 and self.fillings[tipo] > 0:
                        sleep(0.5)
                        time += 0.5
                        taco_state += 0.5
                        self.fillings[tipo] -= 1
                        print("Taquero {0} agrego la otra media tortilla de la orden {1}".format(self.name, order["part_id"]))
                        logging.info("Taquero {0} agrego la otra media tortilla de la orden {1}".format(self.name, order["part_id"]))

                    # Poner un ingrediente
                    elif taco_state >= 1 and size > 0 and self.fillings[order["ingredients"][int(taco_state) - 2]] > 0:
                        sleep(0.5)
                        time += 0.5
                        taco_state += 1
                        self.fillings[order["ingredients"][int(taco_state) - 2]] -= 1
                        print("Taquero {0} agrego {1} a la orden {2}".format(self.name, order["ingredients"][int(taco_state) - 2], order["part_id"]))
                        logging.info("Taquero {0} agrego {1} a la orden {2}".format(self.name, order["ingredients"][int(taco_state) - 2], order["part_id"]))

                    else:
                        break

                    # Revisar si ya esta hecho el taco
                    if taco_state == size + 1:
                        taco_state = 0
                        order["complete_tacos"] += 1
                        print("Taquero {0} termino un taco de la orden {1}".format(self.name, order["part_id"]))
                        logging.info("Taquero {0} termino un taco de la orden {1}".format(self.name, order["part_id"]))

                        self.rest += 1
                        if self.fan_on is False:
                            self.fan += 1
                            if self.fan == 600:
                                self.fan = 0
                                fan_thread = threading.Thread(target=self.fan_control, args=())
                                fan_thread.start()
                        if self.rest == 1000:
                            self.rest = 0
                            self.resting()

                        if order["complete_tacos"] == order["quantity"]:
                            order["status"] = "complete"
                            # Quitar orden del queue
                            print("Taquero {0} termino de preparar la orden {1}".format(self.name, order["part_id"]))
                            logging.info("Taquero {0} termino de preparar la orden {1}".format(self.name, order["part_id"]))
                            self.complete(order)
                            self.queue_taquero.pop(num)
                            finish = True
                            break
                
                if finish is False:
                    order["taco_state"] = taco_state
                    print("Taquero {0} paso a la siguiente orden {1}".format(self.name, order["part_id"]))
                    logging.info("Taquero {0} paso a la siguiente orden {1}".format(self.name, order["part_id"]))
                num += 1
                if num >= len(self.queue_taquero):
                    num = 0


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
                    logging.info("Se agrego la orden {0} del taquero {1}".format(i["part_id"], self.name))

            id += 1

        return id - 1


    def complete(self, order):
        num = ""

        for i in order["part_id"]:
            if i == "-":
                break
            num += i

        complete = True
        for i in queue[int(num)]["orden"]:
            if i["status"] != "complete":
                complete = False
        
        if complete is True:
            queue[int(num)]["status"] = "complete"
            queue[int(num)]["end_time"] = str(datetime.now())
            print("La orden {0} se termino el {1}".format(num, queue[int(num)]["end_time"]))
            logging.info("La orden {0} se termino el {1}".format(num, queue[int(num)]["end_time"]))



# esta persona se encarga de hacer quesadillas y mandarlas a los taqueros, idealmente nunca deja de hacer quesadillas
# si todos los taqueros tienen 5 quesadillas, la personas va a poner las extras en un stack de quesadillas (que nunca se enfrian :O)
# parametros: name = nombre de la quesadillera, t1,...t4 = lista de los taqueros 
class Quesadillas():
    def __init__(self, name, t1, t2, t3, t4):
        self.name = name
        self.quesadillas = 0
        self.taqueros = [t1, t2, t3, t4]
    
    # 20s por quesadilla
    def preparar_quesadillas(self):
        while True:
            work = False
            for i in self.taqueros:
                if len(i.queue_taquero) > 0:
                    work = True
            
            if work is True:
                print(f"Quesadillera {self.name} esta preparando una quesadilla")
                logging.info(f"Quesadillera {self.name} esta preparando una quesadilla")
                sleep(20)
                self.quesadillas += 1
                print(f"Quesadillera {self.name} termino una quesadilla")
                logging.info(f"Quesadillera {self.name} termino una quesadilla")
                


    # Para que de quesadillas a los taqueros
    def dar_quesadilla(self):
        num = 0

        while True:
            if self.taqueros[num].fillings["quesadillas"] < 5 and self.quesadillas > 0 and len(self.taqueros[num].queue_taquero) > 0:
                self.taqueros[num].fillings["quesadillas"] += 1
                self.quesadillas -= 1
                print(f"Quesadillera {self.name} le dio una quesadilla a {self.taqueros[num].name}")
                logging.info(f"Quesadillera {self.name} le dio una quesadilla a {self.taqueros[num].name}")

            num += 1
            if num == 4:
                num = 0



class Chalan():
    def __init__(self, name, taquero1, taquero2):
        self.name = name
        self.taqueros = [taquero1, taquero2] # lista de taqueros del chalan
        self.ingredientes = {"salsa": 0, "guacamole": 0, "cilantro": 0, "cebolla": 0, "tortillas": 0}


    # rellenar los fillings de un taquero en especifico
    # tiempos = {"cilantro":10, "cebolla":10, "salsa":15, "guacamole":20, "tortillas":5}
    # aplicar el ciclo infinito para que el chalan nunca deje de trabajar
    # paramentros: num = numero del taquero
    def rellenar_fillings(self):
        num = 0

        while True:
            tiempo = 0
            refill = False
            
            for i in self.ingredientes:
                self.ingredientes[i] = MAX_FILLINGS[i] - self.taqueros[num].fillings[i]
                tiempo += (self.ingredientes[i] * REFILL_TIME[i]) / MAX_FILLINGS[i]
                if self.ingredientes[i] > 0:
                    refill = True

            if refill is True:
                print(f"Chalan {self.name} esta rellenando los ingredientes del taquero {self.taqueros[num].name}")
                logging.info(f"Chalan {self.name} esta rellenando los ingredientes del taquero {self.taqueros[num].name}")
                sleep(tiempo)

                for i in self.ingredientes:
                    if self.ingredientes[i] > 0:
                        self.taqueros[num].fillings[i] += self.ingredientes[i]
                        print(f"Chalan {self.name} relleno al taquero {self.taqueros[num].name} {self.ingredientes[i]} de {i}")
                        logging.info(f"Chalan {self.name} relleno al taquero {self.taqueros[num].name} {self.ingredientes[i]} de {i}")
            
            if num == 0:
                num = 1
            else:
                num = 0



# -------------------------------------------------------------------

t1 = Taquero('Kench', ['tripa', 'cabeza'])
t2 = Taquero('Zac', ['asada', 'suadero'])
t3 = Taquero('Tahm', ['asada', 'suadero'])
t4 = Taquero('Maokai', ['adobada'])

c1 = Chalan('Riki', t1, t2, )
c2 = Chalan('Federico', t3, t4)

q1 = Quesadillas('Guadalupe', t1, t2, t3, t4)

def init():
    thread_taco1 = threading.Thread(target=t1.make_taco, args=())
    thread_taco2 = threading.Thread(target=t2.make_taco, args=())
    thread_taco3 = threading.Thread(target=t3.make_taco, args=())
    thread_taco4 = threading.Thread(target=t4.make_taco, args=())
    thread_chalan1 = threading.Thread(target=c1.rellenar_fillings, args=())
    thread_chalan2 = threading.Thread(target=c2.rellenar_fillings, args=())
    thread_quesadilla1 = threading.Thread(target=q1.preparar_quesadillas, args=())
    thread_quesadilla2 = threading.Thread(target=q1.dar_quesadilla, args=())

    thread_taco1.start()
    thread_taco2.start()
    thread_taco3.start()
    thread_taco4.start()
    thread_chalan1.start()
    thread_chalan2.start()
    thread_quesadilla1.start()
    thread_quesadilla2.start()

init()

'''
FALTA:
    - cambiar json de los datas
    - agregar una llave con los procesos al json
    - cambiar queues a AWS SQS
    - doc jeje
'''
