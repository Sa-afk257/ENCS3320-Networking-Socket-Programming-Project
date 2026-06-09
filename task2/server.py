from socket import *
import os

# Dictionary for file extensions and their content types
contentTypes = {
    "html": "text/html",
    "css": "text/css",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "mp4": "video/mp4",
}
# Generates a dynamic 404 HTML page
def generate404Page(clientIP, clientPort):
    return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error 404</title>
        </head>
        <body>
            <h1 style="color:red;">The file is not found</h1>
            <p>Client IP: {clientIP}</p>
            <p>Client Port: {clientPort}</p>
        </body>
        </html>
    """


# Helper function to handle HTTP responses
def handleResponse(connectionSocket, statusCode, contentType, content, location=None):
    if statusCode.startswith("307"):  # Redirection
        connectionSocket.send(f"HTTP/1.1 {statusCode}\r\nContent-Type: {contentType}\r\nLocation: {location}\r\n\r\n".encode())
    elif statusCode.startswith("404"):  # 404 Error
        connectionSocket.send(f"HTTP/1.1 {statusCode}\r\nContent-Type: {contentType}\r\n\r\n{content}".encode())
    else:  # Normal response
        connectionSocket.send(f"HTTP/1.1 {statusCode}\r\nContent-Type: {contentType}\r\n\r\n".encode())
        if isinstance(content, bytes):
            connectionSocket.send(content)
        elif isinstance(content, str):
            connectionSocket.send(content.encode())
        else:
            connectionSocket.send(content.read())

# Helper function to serve files
def handleFileRequest(connectionSocket, fileName, clientIP, clientPort):
     
    full_path = os.path.abspath(fileName)
    print(f"[DEBUG] Trying to open file at path: {full_path}") 
    try:
        with open(fileName, 'rb') as file:
            fileExtension = fileName.split('.')[-1]
            contentType = contentTypes.get(fileExtension, "application/octet-stream")
            handleResponse(connectionSocket, "200 OK", contentType, file)
            print(f"Responded with: 200 OK to {clientIP}:{clientPort}")
    except FileNotFoundError:
        print(f"[ERROR] File not found: {full_path}") 
        errorPage = generate404Page(clientIP, clientPort)
        handleResponse(connectionSocket, "404 Not Found", "text/html", errorPage)
        print(f"Responded with: 404 Not Found to {clientIP}:{clientPort}")


# Server setup
serverPort = 9968
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(5)
print(f"The server is ready to listen for requests on port {serverPort}!")

while True:
    connectionSocket, clientAddress = serverSocket.accept()
    clientIP = clientAddress[0]
    clientPort = clientAddress[1]
    HTTPRequest = connectionSocket.recv(2048).decode()

    if not HTTPRequest:
        connectionSocket.close()
        continue

    print(HTTPRequest)
    request = HTTPRequest.split(' ')[1][1:]
    print(f"Requested file: {request}")
 

    if request in ["", "index.html", "main_en.html", "en"]:
        handleFileRequest(connectionSocket, "main_en.html", clientIP, clientPort)

    elif request in ["main_ar.html", "ar"]:
        handleFileRequest(connectionSocket, "main_ar.html", clientIP, clientPort)

    elif request == "mySite_1221618_en.html":
        handleFileRequest(connectionSocket, "mySite_1221618_en.html", clientIP, clientPort)
    elif request == "mySite_1221618_ar.html":
        handleFileRequest(connectionSocket, "mySite_1221618_ar.html", clientIP, clientPort)

    elif request.startswith("handle-request"):
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(request)
        query = parse_qs(parsed.query)
        fileName = query.get("filename", [""])[0]
        filePath = f"media/{fileName}"
        print(f"FILE PATH: {filePath}")

        if fileName.endswith(("png", "jpg", "jpeg")):
            try:
                with open(filePath, "rb") as file:
                    embeddedPage = f"""
                                    <!DOCTYPE html>
                                    <html>
                                    <head>
                                        <title>Image Viewer</title>
                                        <style>
                                            html, body {{
                                                margin: 0;
                                                padding: 0;
                                                height: 100%;
                                            }}
                                            img {{
                                                display: block;
                                                position: absolute;
                                                top: 0; left: 0;
                                                width: 100%;
                                                height: 100%;
                                                object-fit: contain;
                                            }}
                                        </style>
                                    </head>
                                    <body>
                                        <img src="/{filePath}">
                                    </body>
                                    </html>
                                """

                handleResponse(connectionSocket, "200 OK", "text/html", embeddedPage)
                print(f"Responded with: 200 OK (Image) to {clientIP}:{clientPort}")
            except FileNotFoundError:
                redirectURL = f"https://www.google.com/search?q={fileName}&tbm=isch"
                handleResponse(connectionSocket, "307 Temporary Redirect", "text/html", "", location=redirectURL)
                print(f"Redirected to Google Image Search ({fileName}) for {clientIP}:{clientPort}")
        
        elif fileName.endswith("mp4"):
            try:
                with open(filePath, "rb") as file:
                    embeddedPage = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <title>Video Viewer</title>
                                <style>
                                    html, body {{
                                        margin: 0;
                                        padding: 0;
                                        height: 100%
                                        background-color: black;
                                    }}
                                    video {{
                                         display: block;
                                        position: absolute;
                                        top: 0; left: 0;
                                        width: 100%;
                                        height: 100%;
                                        object-fit: contain;
                                    }}
                                </style>
                            </head>
                            <body>
                                <video controls autoplay>
                                    <source src="/{filePath}" type="video/mp4">
                                    Your browser does not support the video tag.
                                </video>
                            </body>
                            </html>
                        """
                    handleResponse(connectionSocket, "200 OK", "text/html", embeddedPage)
                    print(f"Responded with: 200 OK (Video) to {clientIP}:{clientPort}")
            except FileNotFoundError:
                redirectURL = f"https://www.youtube.com/results?search_query={fileName}"
                handleResponse(connectionSocket, "307 Temporary Redirect", "text/html", "", location=redirectURL)
                print(f"Redirected to YouTube ({fileName}) for {clientIP}:{clientPort}")

        else:
            errorPage = generate404Page(clientIP, clientPort)
            handleResponse(connectionSocket, "404 Not Found", "text/html", errorPage)
            print(f"Unsupported file type or not found (404) : {fileName} for {clientIP}:{clientPort}")

    elif request.endswith(tuple(contentTypes.keys())):
        handleFileRequest(connectionSocket, request, clientIP, clientPort)
    

    else:
        errorPage = generate404Page(clientIP, clientPort)
        handleResponse(connectionSocket, "404 Not Found", "text/html", errorPage)
        print(f"Unknown request: {request} from {clientIP}:{clientPort}")

    connectionSocket.close()


# NOTE ::::::  THE COMMAND TO KNOW WITH WHICH PORT THE SOCKET PRIMITTED
#         netstat -a -n -o | findstr :9968

# THE COMMAND TO STOP THE Process
#     taskkill /PID 1234 /F
