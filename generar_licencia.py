import os
import json
import base64
import calendar
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"

def add_months(sourcedate, months):
    """Suma meses calendario de forma robusta manejando bisiestos y días de fin de mes."""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    # Asegura no pasarse del número de días del mes de destino (ej. 31 de enero -> 28/29 de febrero)
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day, 23, 59, 59)

def load_or_create_keys():
    """Carga las llaves Ed25519 existentes o genera un par nuevo si no existen."""
    if os.path.exists(PRIVATE_KEY_FILE):
        with open(PRIVATE_KEY_FILE, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(PUBLIC_KEY_FILE, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
    else:
        print("[-] No se encontraron llaves de firma. Generando nuevo par de llaves Ed25519...")
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Guardar llave privada en formato PEM
        with open(PRIVATE_KEY_FILE, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.OpenSSH,
                    encryption_algorithm=serialization.NoEncryption()
                )
            )

        # Guardar llave pública en formato PEM
        with open(PUBLIC_KEY_FILE, "wb") as f:
            f.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            )
        print("[+] Nuevas llaves criptográficas guardadas en disco local.")
        
    return private_key, public_key

def main():
    print("==================================================")
    print("      SEMS Pro — GENERADOR DE LICENCIAS           ")
    print("==================================================")
    
    private_key, public_key = load_or_create_keys()
    
    # Obtener y mostrar la llave pública en hexadecimal para configurar en el cliente
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    pub_hex = pub_bytes.hex()
    print(f"\n[!] LLAVE PÚBLICA HEX (Configurar en LicenseManager.PUBLIC_KEY_HEX):\n{pub_hex}\n")
    
    email = input("Ingrese el correo electrónico del cliente: ").strip()
    while not email or "@" not in email:
        print("[-] Correo electrónico inválido.")
        email = input("Ingrese el correo electrónico del cliente: ").strip()
        
    print("\nOpciones de Expiración:")
    print("1. Meses exactos de suscripción (Calculo bisiesto/fin de mes automático)")
    print("2. Días específicos de prueba")
    print("3. Ingresar fecha de expiración fija (formato AAAA-MM-DD)")
    
    opcion = input("Seleccione una opción (1/2/3): ").strip()
    
    now = datetime.now()
    if opcion == "1":
        meses = int(input("Ingrese el número de meses: ").strip())
        expiration_date = add_months(now, meses)
    elif opcion == "2":
        dias = int(input("Ingrese los días de prueba: ").strip())
        from datetime import timedelta
        expiration_date = now + timedelta(days=dias)
        expiration_date = expiration_date.replace(hour=23, minute=59, second=59)
    else:
        fecha_str = input("Ingrese la fecha fija (AAAA-MM-DD): ").strip()
        expiration_date = datetime.strptime(fecha_str, "%Y-%m-%d")
        expiration_date = expiration_date.replace(hour=23, minute=59, second=59)
        
    # Construir el payload en formato estandarizado JSON
    payload = {
        "email": email,
        "expires": expiration_date.isoformat()
    }
    
    # Serializar con ordenamiento de llaves para consistencia en la firma
    json_payload = json.dumps(payload, sort_keys=True)
    
    # Firmar el payload utilizando la llave privada
    signature = private_key.sign(json_payload.encode('utf-8'))
    
    # Empaquetar todo
    license_data = {
        "payload": payload,
        "signature": signature.hex()
    }
    
    # Generar token de licencia Base64 final
    license_json = json.dumps(license_data)
    license_token = base64.b64encode(license_json.encode('utf-8')).decode('utf-8')
    
    print("\n==================================================")
    print("DATOS DE LA LICENCIA EMITIDA:")
    print(f"Cliente:    {email}")
    print(f"Expiración: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print("==================================================")
    print("\nCLAVE DE LICENCIA (Enviar completa al cliente):\n")
    print(license_token)
    print("\n==================================================")

if __name__ == "__main__":
    main()
