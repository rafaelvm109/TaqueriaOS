# T.A.C.O.S
Taqueria Algoritmicamente Codificada Operating System

## Table of contents
* [Description](#description)
* [Technologies](#technologies)
* [Launch](#launch)
* [Authors](#authors)

## Description
Final project for Operanting System subject. The project consists of simulating the production line of a taqueria based on a few guidelines presented in a document given by the professor and a few questions taht were discussed during the class. A document explaining our solution can be found [here](https://docs.google.com/document/d/18zPksBr-USmkluBV-36lt6tJbq2uqx0TDGip3c8DBVk/edit?usp=sharing).

## Technologies
* Python 3.9.6
  * libraries
    * boto3
    * datetime
    * json
    * logging
    * threading
    * time
* Amazon SQS

## Launch
* Download or clone this github repository
* install the required python libraries
* run main.py
  * main.py is going to read the orders from tacos.json and send them to SQS, if you want to load the orders directly from SQS comment lines 454-463

## Authors
This project was made by
* [Luis Monroy](https://github.com/Lucobe419)
* [Rafael Viana](https://github.com/rafaelvm109)
