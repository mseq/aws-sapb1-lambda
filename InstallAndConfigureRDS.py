import subprocess
import logging
import socket
import sys

def run(cmd):
    logger.info (f'Starting RD Session Deployment - {cmd}')
    completed = subprocess.run(["powershell", "-Command", cmd], capture_output=True)
    return completed        

# create logger
logging.basicConfig(filename='InstallAndConfigureRDS.log', format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('RDS')
ch = logging.StreamHandler()
logger.setLevel(logging.DEBUG)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port
server_address = ('0.0.0.0', 4489)
logger.info (f'starting up on {server_address[0]} port {server_address[1]}')
sock.bind(server_address)

# Listen for incoming connections
sock.listen(1)

while True:
    # Wait for a connection
    logger.info ('waiting for a connection')
    connection, client_address = sock.accept()

    try:
        logger.info (f'connection from {client_address}')

        # Receive the data in small chunks and retransmit it
        while True:
            data = connection.recv(128)
            logger.info (f'received "{str(data)}"')
            if data:
                if str(data).find("RDS-CONFIG") >= 0:
                    hostname = str(client_address[0]).replace(".", "-") + ".sap.valtellina.corp"
                    logger.info (f'Protocol ok - {str(data)}')
                    logger.info (f'Starting RDS Configuration on server: {hostname}')

                    res = run(f"c:\cfn\AddServerToManager.ps1 {hostname}")
                    res = run(f"New-RDSessionDeployment -ConnectionBroker {hostname} -WebAccessServer {hostname} -SessionHost {hostname}")
                else:
                    logger.info (f'Not ok... Ignore - {str(data)}')
            else :
                logger.info ('End of data')
                break
            
    finally:
        # Clean up the connection
        connection.close()

