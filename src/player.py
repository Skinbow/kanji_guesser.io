class Player:
    def __init__(self, uuid_, nickname):
        self.uuid = uuid_
        self.socketid = None
        self.nickname = nickname
    
    def set_socketid(self, socketid):
        self.socketid = socketid

    def set_publicid(self, publicid):
        self.publicid = publicid