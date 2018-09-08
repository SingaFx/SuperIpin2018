'''
ReadConfig Version 2.0a

'''

class config:

    def __init__(self, configFile):
        self.filename = configFile
        self.readStatus = self.readConfig()

    def readConfig(self):
        f = open(self.filename,'r')

        for line in f:
            if line.find('#') == -1:
                if line.find(';') != -1:
                    newLine=line.replace(';','')
                    newLine=newLine.replace(' ','')
                    newLine=newLine.replace('\n','')
                    cfg_data = newLine.split('=')

                    if cfg_data[0] == 'ip1':
                        self.ip1 = cfg_data[1]
                        # print 'ip1 is ',ip1

                    elif cfg_data[0] == 'ip2':
                        self.ip2 = cfg_data[1]
                        # print 'ip2 is ',ip2

                    elif cfg_data[0] == 'token':
                        self.token = cfg_data[1]
                        # print 'token is ',token

                    elif cfg_data[0] == 'scalping_rule':
                        self.scalping_rule = int(float(cfg_data[1]))

                    elif cfg_data[0] == 'comments':
                        self.comments = cfg_data[1]

                    elif cfg_data[0] == 'chat_id':
                        self.chat_id = int(float(cfg_data[1]))
                        # print 'chat id is ', chat_id

                    elif cfg_data[0] == 'slippage':
                        self.SLIP = int(float(cfg_data[1]))
                        # print 'slippage  is ', SLIP

                    elif cfg_data[0] == 'lots':
                        self.LOTS = float(cfg_data[1])
                        # print 'lots is ', LOTS

                    elif cfg_data[0] == 'risk':
                        self.risk = cfg_data[1]

                    elif cfg_data[0] == 'min_lot':
                        self.min_lot = float(cfg_data[1])

                    elif cfg_data[0] == 'max_profit':
                        self.max_profit = float(cfg_data[1])

                    elif cfg_data[0] == 'lot2usd_ratio':
                        self.lot2usd_ratio = float(cfg_data[1])

                    elif cfg_data[0] == 'symbol':
                        pairs = cfg_data[1]
                        self.symbols=pairs.split(',')
                        # print 'Symbols are ', self.symbols

                    elif cfg_data[0] == 'gap_offset':
                        offset = cfg_data[1]
                        # self.gap_offset=int(float(offset.split(',')))
                        self.gap_offset = [float(i) for i in offset.split(',')]
                        #self.gap_offset = [int(j) for j in self.gap_temp]
                        # print 'gap offset are ', self.gap_offset



                    elif cfg_data[0] == 'suffix_broker_1':
                        if cfg_data[1] == 'none':
                            self.suffix_bro1 = ''
                        else:
                            self.suffix_bro1 = cfg_data[1]

                        # print 'suffix broker 1 is ', suffix_bro1

                    elif cfg_data[0] == 'suffix_broker_2':
                        if cfg_data[1] == 'none':
                            self.suffix_bro2 = ''
                        else:
                            self.suffix_bro2 = cfg_data[1]

                        # print 'suffix broker 2 is', suffix_bro2

                    elif cfg_data[0] == 'arbitrage_open':
                        self.arbitrage_open = int(float(cfg_data[1]))
                        # print 'arbitrage open is  ', arbitrage_open

                    elif cfg_data[0] == 'arbitrage_close':
                        self.arbitrage_close = int(float(cfg_data[1]))
                        # print 'arbitrage close is  ', arbitrage_close

                    elif cfg_data[0] == 'pip_step':
                        self.pip_step = int(float(cfg_data[1]))
                        # print 'pip step is  ', pip_step

                    elif cfg_data[0] == 'stop_loss':
                        self.stop_loss = int(float(cfg_data[1]))

                    elif cfg_data[0] == 'magic_number':
                        self.magic_number = int(float(cfg_data[1]))
                        # print 'magic number is  ', magic_number

                    elif cfg_data[0] == 'start_day':
                        self.start_day = cfg_data[1]

                    elif cfg_data[0] == 'start_time':
                        self.start_time = cfg_data[1]

                    elif cfg_data[0] == 'end_day':
                        self.end_day = cfg_data[1]

                    elif cfg_data[0] == 'end_time':
                        self.end_time = cfg_data[1]

        f.close()

        if len(self.symbols) != len(self.gap_offset):
            return False
        else:
            return True

# readConfig()