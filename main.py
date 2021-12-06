import json
from time import sleep, time
from datetime import datetime
import boto3
import threading
import logging

# CONSTANTES
FILLINGS = ["salsa", "guacamole", "cilantro", "cebolla"]
MAX_FILLINGS = {"salsa": 150, "guacamole": 100, "cilantro": 200, "cebolla": 200, "tortillas": 50, "quesadillas": 5}
REFILL_TIME = {"salsa": 15, "guacamole": 20, "cilantro": 10, "cebolla": 10, "tortillas": 5}
MEAT_TYPES = ["tripa", "cabeza", "asada", "suadero", "adobada"]

# queue principal del sistema, almacena las ordenes y los taqueros la agarran de este queue
queue = []

# configuraciones basicas para crear el archivo de logs
logging.basicConfig(filename='logs.log', format='%(asctime)s %(message)s', filemode='w', datefmt='%m/%d/%Y %H:%M:%S', encoding='utf-8', level=logging.DEBUG)

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
    message = response["Messages"]
    orden = json.loads(message[0]["Body"])
    return message[0], orden

# revisa el queue de SQS y en caso de que el queue tenga mensajes las va a pasar al queue principal de nuestro sistema
# en caso de que no hayan nuevos mensajes solo va a escribir un mensaje en logs, finalmente duerme por 30 segundos
def revisar_queue():
    while(True):
        n_messages = get_number_messages()
        if n_messages > 0:
            for i in range(get_number_messages()):
                message = read_message()
                queue.append(message[1])
                print("se agregó la orden {0}".format(queue[i]["request_id"]))
                logging.info("se agregó la orden {0}".format(queue[i]["request_id"]))

        else:
            print("No hay ordenes nuevas en el queue")
            logging.info("No hay ordenes nuevas en el queue")
        sleep(30)

# CLASES
# clase del taquero, encargado de hacer los tacos y revisar el queue principal para obtener mas ordenes
class Taquero():
    def __init__(self, name, carnes):
        self.name = name # nombre del taquero
        self.carnes = carnes # carnes que maneja
        self.fillings = {"salsa": 150, "guacamole": 100, "cilantro": 200, "cebolla": 200, "tortillas": 50, "quesadillas": 5} # cantidad que tiene de cada filling
        self.rest = 0 # 1000 tacos -> 30 segundos de descanso
        self.fan = 0 # 600 tacos -> prender ventilador por 60
        self.fan_on = False # bool que controla el ventilador
        self.queue_taquero = [] # queue individual taquero
        self.finished = False # determina si el trabajo del taquero ya se termino

    # funcion para que el taquero descanse 30 segundos
    def resting(self):
        print(f"Taquero {self.name} empezó su descanso")
        logging.info(f"Taquero {self.name} empezó su descanso")
        sleep(30)
        print(f"Taquero {self.name} terminó su descanso")
        logging.info(f"Taquero {self.name} terminó su descanso")
        # si el queue esta vacio tambien puede descansar
    
    # controla el fan, prende/apaga en un intervalo de 60s
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
  
    def make_taco(self):
        num = 0 # La orden en la que trabajara el taquero
        id = 0 # El id de la orden, sirve para recordar donde se quedo en el queue principal
        finish = True # Para saber si el taquero termino una orden

        while True:
            # Al inicio del while o si el taquero termino una orden, busca ordenes en el queue principal
            if finish is True:
                id = self.get_orders(id)
                finish = False

            if len(self.queue_taquero) > 0:
                # Hacer taco y agregar ingredientes, al terminar un taco, se cambia el contador y se reinicia el estado del taco
                # Si se acaba el tiempo, se guarda el estado del taco y el numero de tacos
                now = time() * 1000 # Para saber cuanto tarda en hacer una accion
                order = self.queue_taquero[num] # La orden en la que se trabajara
                taco_state = order["taco_state"] # Obtiene el estado en el que se quedo el ultimo taco
                size = len(order["ingredients"]) # Para saber cuantos ingredientes lleva el taco
                tipo = "quesadillas" # Se define el tipo de taco como quesadilla por default
                tiempo = 0 # Para saber cuanto tiempo lleva el taquero trabajando en el taco
                finish = False

                # Revisa si se deben de preparar tacos y cambia de quesadillas a torillas
                if order["type"] == "taco":
                    tipo = "tortillas"

                print("Taquero {0} inicio con la orden {1}".format(self.name, order["part_id"]))
                logging.info("Taquero {0} inicio con la orden {1}".format(self.name, order["part_id"]))
                order["response"].append({
                        "who": self.name,
                        "when": str(datetime.now()),
                        "what": "Se inició con la orden {0}".format(order["part_id"]),
                        "time": round((time() * 1000) - now)
                    })

                # El taquero trabajara por 5 segundos en cada orden
                while tiempo < 5:
                    now = time() * 1000 # Para saber cuanto tarda en hacer una accion
                    # Poner la tortilla
                    if taco_state == 0 and self.fillings[tipo] > 0:
                        # Si no hay suficiente tiempo para poner la tortilla, pone solo la mitad en 0.5 segundos
                        if tiempo == 4.5:
                            sleep(0.5)
                            tiempo += 0.5
                            taco_state += 0.5
                            print("Taquero {0} preparo media tortilla de la orden {1}".format(self.name, order["part_id"]))
                            logging.info("Taquero {0} preparo media tortilla de la orden {1}".format(self.name, order["part_id"]))
                            order["response"].append({
                                "who": self.name,
                                "when": str(datetime.now()),
                                "what": "Se puso media tortilla",
                                "time": round((time() * 1000) - now)
                            })
                        else:
                            # Si hay tiempo suficiente, pone la tortilla entera
                            sleep(1)
                            tiempo += 1
                            taco_state += 1
                            self.fillings[tipo] -= 1
                            print("Taquero {0} preparo una tortilla de la orden {1}".format(self.name, order["part_id"]))
                            logging.info("Taquero {0} preparo una tortilla de la orden {1}".format(self.name, order["part_id"]))
                            order["response"].append({
                                "who": self.name,
                                "when": str(datetime.now()),
                                "what": "Se puso una tortilla",
                                "time": round((time() * 1000) - now)
                            })
                    # Poner media tortilla
                    elif taco_state == 0.5 and self.fillings[tipo] > 0:
                        # Pone la otra mitad de la tortilla si es que no hubo tiempo suficiente un tiempo atras
                        sleep(0.5)
                        tiempo += 0.5
                        taco_state += 0.5
                        self.fillings[tipo] -= 1
                        print("Taquero {0} agrego la otra media tortilla de la orden {1}".format(self.name, order["part_id"]))
                        logging.info("Taquero {0} agrego la otra media tortilla de la orden {1}".format(self.name, order["part_id"]))
                        order["response"].append({
                                "who": self.name,
                                "when": str(datetime.now()),
                                "what": "Se puso otra media tortilla",
                                "time": round((time() * 1000) - now)
                            })
                    # Poner un ingrediente
                    elif taco_state >= 1 and size > 0 and self.fillings[order["ingredients"][int(taco_state) - 2]] > 0:
                        # Se revisa el estado del taco y se agrega el ingrediente correspondiente
                        sleep(0.5)
                        tiempo += 0.5
                        taco_state += 1
                        self.fillings[order["ingredients"][int(taco_state) - 2]] -= 1
                        print("Taquero {0} agrego {1} a la orden {2}".format(self.name, order["ingredients"][int(taco_state) - 2], order["part_id"]))
                        logging.info("Taquero {0} agrego {1} a la orden {2}".format(self.name, order["ingredients"][int(taco_state) - 2], order["part_id"]))
                        order["response"].append({
                                "who": self.name,
                                "when": str(datetime.now()),
                                "what": "Se agregó {0}".format(order["ingredients"][int(taco_state) - 2]),
                                "time": round((time() * 1000) - now)
                            })
                    # Si el taquero no puede hacer ninguna de las acciones pasadas, termina y pasa a la siguiente orden
                    else:
                        break

                    # Revisar si ya esta hecho el taco
                    if taco_state == size + 1:
                        # Si el estado del taco esta al maximo, se toma como completo y se agrega un taco al contador,
                        # ademas de reiniciar el estado del taco
                        now = time() * 1000
                        taco_state = 0
                        order["complete_tacos"] += 1
                        print("Taquero {0} termino un taco de la orden {1}".format(self.name, order["part_id"]))
                        logging.info("Taquero {0} termino un taco de la orden {1}".format(self.name, order["part_id"]))
                        order["response"].append({
                                "who": self.name,
                                "when": str(datetime.now()),
                                "what": "Terminó un taco",
                                "time": round((time() * 1000) - now)
                            })

                        self.rest += 1
                        # Si ya van 600 tacos, prende el ventilador
                        if self.fan_on is False:
                            self.fan += 1
                            if self.fan == 600:
                                self.fan = 0
                                fan_thread = threading.Thread(target=self.fan_control, args=())
                                fan_thread.start()
                        # Si ya van 1000 tacos, toma un descanso
                        if self.rest == 1000:
                            self.rest = 0
                            self.resting()

                        # Revisa si ya se terminaron todos los tacos de la orden para marcarla como completa
                        if order["complete_tacos"] == order["quantity"]:
                            now = time() * 1000
                            order["status"] = "complete"
                            # Quitar orden del queue
                            print("Taquero {0} termino de preparar la orden {1}".format(self.name, order["part_id"]))
                            logging.info("Taquero {0} termino de preparar la orden {1}".format(self.name, order["part_id"]))
                            order["response"].append({
                                "who": self.name,
                                "when": str(datetime.now()),
                                "what": "Se terminó la orden",
                                "time": round((time() * 1000) - now)
                            })
                            print(order["response"])
                            self.complete(order)
                            self.queue_taquero.pop(num)
                            finish = True
                            self.finished = self.finished_workload(id)
                            break
                
                # Si el taquero no termino de preparar la orden, se guarda el estado del taco antes de pasar
                # a la siguiente orden
                if finish is False:
                    order["taco_state"] = taco_state
                    print("Taquero {0} paso a la siguiente orden {1}".format(self.name, order["part_id"]))
                    logging.info("Taquero {0} paso a la siguiente orden {1}".format(self.name, order["part_id"]))

                # Se cambia el numero de orden
                num += 1
                if num >= len(self.queue_taquero):
                    num = 0

            # Si el taquero ya termino todo su trabajo, hace un break
            if self.finished is True:
                break

    # revisa las ordenes del queue principal y las agrega al queue especifico del taquero
    # parametros: id = id de la ultima orden revisada por el taquero
    def get_orders(self, id):
        # Si el taquero ya tiene 5 ordenes en su queue o termino de revisar todas las ordenes, tambien se detendra.
        while len(self.queue_taquero) < 5 and len(queue) > id:
            order = queue[id]["orden"]

            for i in order:
                # Agregar orden al queue del taquero
                if i["meat"] in self.carnes and i["status"] == "open" and len(self.queue_taquero) < 5:
                    now = time() * 1000
                    i["status"] = "taken"
                    self.queue_taquero.append(i)
                    # Agregar las variables
                    i["taco_state"] = 0
                    i["complete_tacos"] = 0
                    i["response"] = [{
                        "who": self.name,
                        "when": str(datetime.now()),
                        "what": "Se agregó la orden",
                        "time": (time() * 1000) - now
                    }]
                    print("Se agrego la orden {0} del taquero {1}".format(i["part_id"], self.name))
                    logging.info("Se agrego la orden {0} del taquero {1}".format(i["part_id"], self.name))

            id += 1
            self.finished = self.finished_workload(id)

        return id - 1

    # revisa si la orden esta completa, revisando el status de cada una de las subordendes
    # parametros: order = suborden del taquero
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

    # revisa si todos los queues estan vacios retornando falso o verdadero
    def finished_workload(self, id):
        n_messages = get_number_messages()
        if id >= len(queue) and len(self.queue_taquero) == 0 and n_messages == 0:
            return True
        else:
            return False


# esta persona se encarga de hacer quesadillas y mandarlas a los taqueros (20 segundos por quesadilla)
# al terminar una quesadilla la guarda en su stack y revisa si alguno de los taqueros necesita una quesadilla
# parametros: name = nombre de la quesadillera, t1,...t4 = lista de los taqueros 
class Quesadillas():
    def __init__(self, name, t1, t2, t3, t4):
        self.name = name # nombre 
        self.quesadillas = 0 # Numero de quesadillas en su stack
        self.taqueros = [t1, t2, t3, t4] # lista de los taqueros
    
    # 20s por quesadilla
    # funcion que permite que la persona de las quesadillas prepare las qusadillas
    # tambien es la encargada de revisar que todos los taqueros ya terminaron de trabajar
    def preparar_quesadillas(self):
        while True:
            count = 0 # Para contar a los taqueros que ya terminaron todo

            # Revisa cuantos taqueros ya terminaron todo
            for i in self.taqueros:
                if i.finished is True:
                    count += 1

            # Si todos los taqueros ya terminaron, hace break
            if count == 4:
                break
            
            # Prepara una quesadilla y la agrega a su stack
            print(f"Quesadillera {self.name} esta preparando una quesadilla")
            logging.info(f"Quesadillera {self.name} esta preparando una quesadilla")
            sleep(20)
            self.quesadillas += 1
            print(f"Quesadillera {self.name} termino una quesadilla")
            logging.info(f"Quesadillera {self.name} termino una quesadilla")

    # Para que de quesadillas a los taqueros
    def dar_quesadilla(self):
        num = 0 # Para cambiar de taquero

        while True:
            count = 0 # Para contar a los taqueros que ya terminaron todo

            # Revisa cuantos taqueros ya terminaron
            for i in self.taqueros:
                if i.finished is True:
                    count += 1

            # Si todos los taqueros ya terminaron, hace break
            if count == 4:
                break

            # Revisa si el taquero le hacen faltan quesadillas, si todavia esta trabajando y si hay suficientes quesadillas
            if self.taqueros[num].fillings["quesadillas"] < 5 and self.quesadillas > 0 and self.taqueros[num].finished is False:
                # Le entrega una quesadilla al taquero
                self.taqueros[num].fillings["quesadillas"] += 1
                self.quesadillas -= 1
                print(f"Quesadillera {self.name} le dio una quesadilla a {self.taqueros[num].name}")
                logging.info(f"Quesadillera {self.name} le dio una quesadilla a {self.taqueros[num].name}")

            # Cambia de taquero
            num += 1
            if num == 4:
                num = 0
        
        # Imprimir todo lo que sobro
        for i in self.taqueros:
            print(f"Al taquero {i.name} le sobro lo siguiente:\n{i.fillings}\n")
        print(f"A la quesadillera {self.name} le sobraron {self.quesadillas} quesadillas")



class Chalan():
    def __init__(self, name, taquero1, taquero2):
        self.name = name # nombre del chalan
        self.taqueros = [taquero1, taquero2] # lista de taqueros del chalan
        self.ingredientes = {"salsa": 0, "guacamole": 0, "cilantro": 0, "cebolla": 0, "tortillas": 0} # ingredientes 

    # rellenar los fillings de un taquero en especifico
    # tiempos = {"cilantro":10, "cebolla":10, "salsa":15, "guacamole":20, "tortillas":5}
    def rellenar_fillings(self):
        num = 0 # Para identificar al taquero que atendera el chalan

        while True:
            tiempo = 0 # Para el tiempo que tardara en rellenar ingredientes
            refill = False # Identifica si tiene que rellenar algo
            count = 0 # Cuenta el numero de taqueros que ya terminaron todo
            
            # Revisa si sus taqueros ya dejaron de trabajar
            for i in self.taqueros:
                if i.finished is True:
                    count += 1

            # Si ambos taqueros ya terminaron, hace break
            if count == 2:
                break

            # Revisa si el taquero sigue trabajando
            if self.taqueros[num].finished is False:
                # Revisa los ingredientes que le faltan al taquero y agrega el tiempo que tomara ir por ellos
                for i in self.ingredientes:
                    self.ingredientes[i] = MAX_FILLINGS[i] - self.taqueros[num].fillings[i]
                    tiempo += (self.ingredientes[i] * REFILL_TIME[i]) / MAX_FILLINGS[i]
                    if self.ingredientes[i] > 0:
                        refill = True

                # Confirma si hay que rellenar algo
                if refill is True:
                    print(f"Chalan {self.name} esta rellenando los ingredientes del taquero {self.taqueros[num].name}")
                    logging.info(f"Chalan {self.name} esta rellenando los ingredientes del taquero {self.taqueros[num].name}")
                    sleep(tiempo)

                    # Rellena los ingredientes
                    for i in self.ingredientes:
                        if self.ingredientes[i] > 0:
                            self.taqueros[num].fillings[i] += self.ingredientes[i]
                            print(f"Chalan {self.name} relleno al taquero {self.taqueros[num].name} {self.ingredientes[i]} de {i}")
                            logging.info(f"Chalan {self.name} relleno al taquero {self.taqueros[num].name} {self.ingredientes[i]} de {i}")
            
            # Cambia de taquero
            if num == 0:
                num = 1
            else:
                num = 0

# -------------------------------------------------------------------

# Se crean los taqueros, chalanes y quesadillera
t1 = Taquero('Kench', ['tripa', 'cabeza'])
t2 = Taquero('Zac', ['asada', 'suadero'])
t3 = Taquero('Tahm', ['asada', 'suadero'])
t4 = Taquero('Maokai', ['adobada'])

c1 = Chalan('Riki', t1, t2, )
c2 = Chalan('Federico', t3, t4)

q1 = Quesadillas('Guadalupe', t1, t2, t3, t4)

# funcion init donde se crea el queue y cada uno de los threads
def init():
    # asegura que el queue de SQS este vacio (solo se puede correr una vez cada 60s)
    sqs.purge_queue(QueueUrl=queue_url)

    # abrimos el archivo de tacos.json para rellenar el queue con las ordenes de ese archivo
    with open('TaquerisOS-main/tacos.json') as f:
        data = json.load(f)

    # mandamos todas las ordenes del json al Queue de SQS
    for i in range(len(data)):
        sqs.send_message(QueueUrl=queue_url, MessageBody=(json.dumps(data[i])))

    # Se crea e inicia el thread que obtendra las ordenes
    rev_q = threading.Thread(target=revisar_queue, args=())
    rev_q.start()
    sleep(5) # sleep de 5 segundos para asegurar que el thread de revisar queue sea el primero en correr

    # Se crean los threads para los taqueros, chalanes y quesadillera
    thread_taco1 = threading.Thread(target=t1.make_taco, args=())
    thread_taco2 = threading.Thread(target=t2.make_taco, args=())
    thread_taco3 = threading.Thread(target=t3.make_taco, args=())
    thread_taco4 = threading.Thread(target=t4.make_taco, args=())
    thread_chalan1 = threading.Thread(target=c1.rellenar_fillings, args=())
    thread_chalan2 = threading.Thread(target=c2.rellenar_fillings, args=())
    thread_quesadilla1 = threading.Thread(target=q1.preparar_quesadillas, args=())
    thread_quesadilla2 = threading.Thread(target=q1.dar_quesadilla, args=())

    # Se inician los threads de los taqueros, chalanes y quesadilleras
    thread_taco1.start()
    thread_taco2.start()
    thread_taco3.start()
    thread_taco4.start()

    sleep(2)

    thread_chalan1.start()
    thread_chalan2.start()
    thread_quesadilla1.start()
    thread_quesadilla2.start()

# llamamos a la funcion init() para correr el programa
init() 
