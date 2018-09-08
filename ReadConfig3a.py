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
    
                    if cfg_data[0] == 'slave_ips':
                        ip = cfg_data[1]
                        self.s_ips=ip.split(',')
                        
                    elif cfg_data[0] == 'master_ip':
                        self.m_ip = cfg_data[1]
                        
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
                        risk = cfg_data[1]
                        self.risks = risk.split(',')
    
                    elif cfg_data[0] == 'min_lot':
                        self.min_lot = float(cfg_data[1])
    
                    elif cfg_data[0] == 'max_profit':
                        self.max_profit = float(cfg_data[1])
    
                    elif cfg_data[0] == 'lot2usd_ratio':
                        ratio = cfg_data[1]
                        temp = ratio.split(',')
                        
                        self.lot2usd_ratio = []
                        for t in temp:
                            self.lot2usd_ratio.append(float(t))
    
                    elif cfg_data[0] == 'symbol':
                        pairs = cfg_data[1]
                        self.symbols=pairs.split(',')
                        # print 'Symbols are ', self.symbols
    
                    elif cfg_data[0] == 'gap_offset':
                        raw_offset = cfg_data[1]
                        temp_offsets = raw_offset.split('n')
                        
                        self.gap_offset = []
                        for gap_offset in temp_offsets:
                            gap_offset = gap_offset.replace('[','')
                            gap_offset = gap_offset.replace(']','')                           
                            gp = [float(i) for i in gap_offset.split(',')]
                            self.gap_offset.append(gp)
                                                                        
                    elif cfg_data[0] == 'master_suffix':
                        self.m_suffix = cfg_data[1]
                                            
                    elif cfg_data[0] == 'slave_suffixs':
                        suffix = cfg_data[1]
                        self.s_suffixs = suffix.split(',')
                        
                        for s in range(len(self.s_suffixs)):
                            if self.s_suffixs[s] == 'None':
                                self.s_suffixs[s] = ''
                    
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
                
#        print('ip length =',len(self.ips))
#        print('offset length =',len(self.gap_offset))
#        
        status = False
        import sys
        
        if len(self.s_ips) == len(self.gap_offset):
            status = True
            print('OK !!! gap offset and ips are same length')
        else:
            status = False
            print('Error !!! gap offset and ips are not same length')
            sys.exit()
            
            
        for offset in self.gap_offset:
            if len(self.symbols) == len(offset):
                status = True
                print('OK !!! symbol and gap_offset are same length')
            else:
                status = False
                print('Error !!! symbol and gap_offset are not same length')
                sys.exit()
                
        return status

if __name__ == "__main__":
#readConfig('superipin.cfg')
    cfgData = config('superipin.cfg')
    config.readConfig()