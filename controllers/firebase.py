
import os
import requests
import json
import logging
import traceback

from dotenv import load_dotenv
from fastapi import HTTPException, Depends


import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from utils.database import fetch_query_as_json, get_db_connection
from utils.security import create_jwt_token
from models.Userlogin import UserRegister

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


# Inicializar la app de Firebase Admin leyendo el json
cred = credentials.Certificate("secrets/medicdatafirebase-adminsdk.json")
firebase_admin.initialize_app(cred)



async def register_user_firebase(user: UserRegister):
    try:
        # Crear usuario en Firebase Authentication
        user_record = firebase_auth.create_user(
            email=user.email,
            password=user.password
        )

        conn = await get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "EXEC md.crear_usuario @usuario = ?, @nombre = ?, @correo = ?",
                user_record.uid,
                user.name,
                user.email
            )
            conn.commit()
            return {
                "success": True,
                "message": "Usuario registrado exitosamente"
            }
        except Exception as e:
            firebase_auth.delete_user(user_record.uid)
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error al registrar usuario: {e}"
        )




#####################################################################
async def login_user_firebase(user: UserRegister):
    try:
        # Obtener la clave API desde las variables de entorno
        api_key = os.getenv("FIREBASE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Firebase API key not set")

        # Autenticar usuario con Firebase Authentication usando la API REST
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": user.email,
            "password": user.password,
            "returnSecureToken": True
        }
        
        response = requests.post(url, json=payload)
        response_data = response.json()

        if response.status_code != 200:
            error_message = response_data.get('error', {}).get('message', 'Unknown error')
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Error al autenticar usuario: {error_message}"
            )

        query = f"SELECT activo FROM md.usuarios WHERE correo = '{user.email}'"

        try:
            logger.info("Executing query to check user status")
            result_json = await fetch_query_as_json(query)

            logger.info(f"Query result: {result_json}")
            
            if result_json is None:  # Maneja el caso donde no hay datos
                raise HTTPException(status_code=404, detail="No data returned from database")
            
            # Manejar diferentes tipos de resultados
            if isinstance(result_json, str):
                result_dict = json.loads(result_json)
            elif isinstance(result_json, list):
                result_dict = result_json
            else:
                raise HTTPException(status_code=500, detail="Unexpected data type returned from database")
            
            logger.info(f"Loaded result dict: {result_dict}")

            if not result_dict:
                raise HTTPException(status_code=404, detail="User not found in database")


            # Verificar si el primer elemento es un diccionario y contiene la clave "activo"
            if isinstance(result_dict[0], dict) and "activo" in result_dict[0]:
                activo_value = result_dict[0]["activo"]
                logger.info(f"Activo value: {activo_value}")
            else:
                logger.error("El primer elemento de result_dict no es un diccionario o no contiene la clave 'activo'")
                raise HTTPException(status_code=500, detail="Error en la estructura de datos del resultado")

            logger.info("Segunda parada")

            if not isinstance(activo_value, int):
                logger.error(f"Unexpected type for 'activo' value: {type(activo_value)}")
                raise HTTPException(status_code=500, detail="Unexpected type for 'activo' value")

            logger.info("Tercera parada")

            # Convertir activo_value a cadena si es necesario (esto parece no ser necesario aquí)
            return {
                "message": "Usuario autenticado exitosamente",
                "idToken": create_jwt_token(user.email,  result_dict[0]["activo"])
            }

        except Exception as db_exception:
            logger.error(f"Database error: {str(db_exception)}")
            raise HTTPException(status_code=500, detail="Database query failed")

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        error_detail = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        logger.error(f"Unexpected error: {error_detail}")
        raise HTTPException(
            status_code=400,
            detail=f"Error al registrar usuario: {error_detail}"
        )