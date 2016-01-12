# from http.server import BaseHTTPRequestHandler, HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Restaurant, MenuItem

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
session = DBSession()
port = 8080

class webserverHandler(BaseHTTPRequestHandler):
    # Overridden method from BaseHTTPRequestHandler class
    def do_GET(self):
        try:
            if self.path.endswith("/hello"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body>"
                output += "<h1>Hello!</h1>"
                output += '''<form method='POST' enctype='multipart/form-data' action='/hello'><h2>What would you like me to say?</h2><input name="message" type="text" ><input type="submit" value="Submit"> </form>'''
                output += "</body></html>"
                self.wfile.write(output)
                print(output)
                return
            if self.path.endswith("/hola"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body>"
                output += "<h1>&#161 Hola !</h1>"
                output += '''<form method='POST' enctype='multipart/form-data' action='/hello'><h2>What would you like me to say?</h2><input name="message" type="text" ><input type="submit" value="Submit"> </form>'''
                output += "</body></html>"
                self.wfile.write(output)
                print(output)
                return
            if self.path.endswith("/restaurants"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body>"
                restaurants = session.query(Restaurant).all()
                for restaurant in restaurants:
                    output += "<h2>" + restaurant.name + "</h2>"
                    output += '''<a href="http://localhost:''' + str(port) + '''/restaurant/''' + str(restaurant.id)
                    output += '''/edit">'''
                    output += "Edit</a>"
                    output += ''' <a href="http://localhost:''' + str(port) + '''/restaurant/''' + str(restaurant.id)
                    output += '''/delete">'''
                    output += "Delete</a>"
                    output += "</body></html>"
                self.wfile.write(output)
                print(output)
                return
            if self.path.endswith("/edit"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body>"
                path_contents = self.path.split("/")
                try:
                    if path_contents[len(path_contents)-1] == 'edit':
                        restaurant_id = path_contents[len(path_contents)-2]
                        restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
                        output += "<h2>" + restaurant.name + "</h2>"
                        output += '''<form method='POST' enctype='multipart/form-data' action='/restaurant'''
                        output += '''/''' + str(restaurant_id) + '''/edit'>'''
                        output += '''<h2>What will be the new name of the restaurant?</h2>'''
                        output += '''<input name="message" type="text" ><input type="submit" value="Submit"> </form>'''
                        output += "</body></html>"
                        self.wfile.write(output)
                        print(output)
                        return
                except:
                    pass
            if self.path.endswith("/new"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body>"
                output += '''<form method='POST' enctype='multipart/form-data' action='/restaurant/new'>'''
                output += '''<h2>What will be the name of the new restaurant?</h2>'''
                output += '''<input name="message" type="text" ><input type="submit" value="Submit"> </form>'''
                output += "</body></html>"
                self.wfile.write(output)
                print(output)
                return
            if self.path.endswith("/delete"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body>"
                path_contents = self.path.split("/")
                try:
                    if path_contents[len(path_contents)-1] == 'delete':
                        restaurant_id = path_contents[len(path_contents)-2]
                        output += '''<form method='POST' enctype='multipart/form-data' action='/restaurant/'''
                        output += restaurant_id + '''/delete'>'''
                        output += '''<h2>Are you sure you want to delete this restaurant?</h2>'''
                        output += '''<input type="submit" name="delete" value="Delete" />'''
                        output += '''</form>'''
                        output += "</body></html>"
                        self.wfile.write(output)
                        print(output)
                        return
                except:
                    pass
        except IOError:
            self.send_error(404, "File Not Found {}".format(self.path))

    # Overridden method from BaseHTTPRequestHandler class
    def do_POST(self):
        if self.path.endswith("/hello"):
            try:
                self.send_response(301)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                ctype, pdict = cgi.parse_header(
                    self.headers.getheader('content-type'))
                if ctype == 'multipart/form-data':
                    fields = cgi.parse_multipart(self.rfile, pdict)
                    messagecontent = fields.get('message')
                    output = ""
                    output += "<html><body>"
                    output += " <h2> Okay, how about this: </h2>"
                    output += "<h1> %s </h1>" % messagecontent[0]
                    output += '''<form method='POST' enctype='multipart/form-data' action='/hello'><h2>What would you
                    like me to say?</h2><input name="message" type="text" ><input type="submit" value="Submit">
                    </form>'''
                    output += "</body></html>"
                    self.wfile.write(output)
                    print(output)
            except:
                pass
        if self.path.endswith("/edit"):
            try:
                self.send_response(301)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                ctype, pdict = cgi.parse_header(
                    self.headers.getheader('content-type'))
                path_contents = self.path.split("/")
                restaurant_id = path_contents[len(path_contents)-2]
                if ctype == 'multipart/form-data':
                    fields = cgi.parse_multipart(self.rfile, pdict)
                    messagecontent = fields.get('message')
                    restaurant_name = messagecontent[0]
                    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
                    restaurant.name = restaurant_name
                    session.commit()
                    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
                    output = ""
                    output += "<html><body>"
                    output += "<h2>" + restaurant.name + "</h2>"
                    output += '''<form method='POST' enctype='multipart/form-data' action='/restaurant'''
                    output += '''/''' + str(restaurant_id) + '''/edit'>'''
                    output += '''<h2>What will be the new name of the restaurant?</h2>'''
                    output += '''<input name="message" type="text" ><input type="submit" value="Submit"> </form>'''
                    output += "</body></html>"
                    self.wfile.write(output)
                    print(output)
            except:
                pass
        if self.path.endswith("/new"):
            try:
                self.send_response(301)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                ctype, pdict = cgi.parse_header(
                    self.headers.getheader('content-type'))
                if ctype == 'multipart/form-data':
                    fields = cgi.parse_multipart(self.rfile, pdict)
                    messagecontent = fields.get('message')
                    restaurant_name = messagecontent[0]
                    restaurant = Restaurant(name = restaurant_name)
                    session.add(restaurant)
                    session.commit()
                    output = ""
                    output += "<html><body>"
                    output += "<h2>" + restaurant.name  + " added!</h2>"
                    output += '''<form method='POST' enctype='multipart/form-data' action='/restaurants/new'>'''
                    output += '''<h2>What will be the name of the new restaurant?</h2>'''
                    output += '''<input name="message" type="text" ><input type="submit" value="Submit"> </form>'''
                    output += "</body></html>"
                    self.wfile.write(output)
                    print(output)
            except:
                pass
        if self.path.endswith("/delete"):
            try:
                path_contents = self.path.split("/")
                restaurant_id = int(path_contents[len(path_contents)-2])
                self.send_response(301)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                print(restaurant_id)
                restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
                print(restaurant.name)
                session.delete(restaurant)
                session.commit()
                output = ""
                output += "<html><body>"
                output += "<h2>" + restaurant.name  + " Deleted!</h2>"
                output += "</body></html>"
                self.wfile.write(output)
                print(output)
            except:
                pass

def main():
    server = HTTPServer(('',port), webserverHandler)
    try:
        print("Webserver running on port {}".format(port))
        server.serve_forever()
    except KeyboardInterrupt:
        print("^C entered. Stopping webserver")
        server.socket.close()


if __name__ == '__main__':
    main()