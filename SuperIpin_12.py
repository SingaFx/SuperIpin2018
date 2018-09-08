'''
30/03/2018 Reb 10.5d - add count arbitrage delay
27/03/2018 Reb 10.5c - debug false signal
26/02/2018 Rev 10.5b - add more data for telegram notify
31/01/2018 Rev 10.5a - Add stop loss parameter

06/01/2018 Rev 10.4a - Add hidden stop loss
                    - Add offset trigger
                    - Add detect market not running

27/12/2017 Rev 10.3d - fixed issue for telegram

26/12/2017 Rev 10.3c - add checkbox for telegram

26/12/2017 Rev 10.3b - put database file in directory

24/12/2017 Rev 10.3a - added export data to CSV with custom sql

24/12/2017 Rev 10.2b - integrate db in the UI

23/12/2017 Rev 10.2a - add database for quotes

20/12/2017 Rev 10.1a - new UI with better handling

16/12/2017 Rev 9.3h - to add condition check for connection before trade

16/12/2017 Rev 9.3g - add debug button for telegram

12/12/2017 Rev 9.3f - this version fix bug for max profit , still check for trade for trade count greater than 0, to close open position

11/12/2017 Rev 9.3e - this version add maximum profit per account

27/11/2017 Rev 9.3d - this version is to remove comment when open order. to avoid from being detected.

20/11/2017 Rev 9.3b - this minor change is for 2 Leg arbitrage ONLY

18/11/2017 Rev 9.3 - add check no trade time
				   - add init function to initialize symbols

'''

import zmq
import math
import os
from time import sleep
from datetime import datetime
import datetime as dt
import sys
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import telegram
import csv
import ReadConfig3a
import validateTime as vt
import write2db as db

app_name = 'SuperIpin 12Beta'
ea_name_ver = 'SuperIpin 12Beta'
zmq_ver_cfg = 'mt4zeromq_1.0'
cfgData = ReadConfig3a.config('superipin.cfg')
# print 'cfgData result =',cfgData.readStatus

#Read from config file
# ----------------------------------------------
master_ip = cfgData.m_ip
slave_ips = cfgData.s_ips
magic_number = cfgData.magic_number
SLIP_param = cfgData.SLIP
LOTS = cfgData.LOTS
RISK = cfgData.risk
minLOT = cfgData.min_lot
lot2usd_ratio = cfgData.lot2usd_ratio
pairs = cfgData.symbols
gaps_offsets = cfgData.gap_offset
master_suffix = cfgData.m_suffix
slave_suffixs = cfgData.s_suffixs
arbitrage_open_param = cfgData.arbitrage_open
arbitrage_close_param = cfgData.arbitrage_close
pip_step_param = cfgData.pip_step
chat_id = cfgData.chat_id
token = cfgData.token
scalpingRuleTime = cfgData.scalping_rule
comments = cfgData.comments
start_day = cfgData.start_day
start_time = cfgData.start_time
end_day = cfgData.end_day
end_time = cfgData.end_time
max_profit = cfgData.max_profit
stop_loss_param = cfgData.stop_loss

cnt_arb_limit = 2
g_bro_index = 0

class MyMainWindow(QMainWindow):

    def __init__(self, parent=None):

        super(MyMainWindow, self).__init__(parent)
        self.form_widget = FormWidget(self)
        self.setCentralWidget(self.form_widget)

        self.setWindowIcon(QIcon('img\\ipin.png'))
        self.setWindowTitle(app_name)
        self.setGeometry(50, 150, 1500, 550)

        self.menu_bar()

    def menu_bar(self):

        extractAction = QAction("&Exit", self)
        extractAction.setShortcut("Ctrl+Q")
        extractAction.setStatusTip('Leave The App')
        extractAction.triggered.connect(self.close_application)

        testMode = QAction("&Test Mode", self)
        testMode.setShortcut("Ctrl+T")
        testMode.setStatusTip('Enter test mode')
        testMode.triggered.connect(self.test_mode)
        self.testScreen = TestWindow(self)


        self.statusBar()

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(extractAction)
        fileMenu = mainMenu.addMenu('&Option')
        fileMenu.addAction(testMode)
        fileMenu = mainMenu.addMenu('&Help')

    def test_mode(self):
        print ('Enter Test Mode')
        self.testScreen.show()

    def close_application(self):
        print("Exit the Application")
        sys.exit()

class FormWidget(QWidget):

    def __init__(self, parent):
        super(FormWidget, self).__init__(parent)

        self.init_ui()
        self.Widget_Init()
        self.previous_tms = datetime.now()
        self.chk_initialization()
        self.chk_mqlVer()
        self.chk_broker_nm()
        self.init_var()
        self.broker_index = 0
        
        global g_bro_index 
        g_bro_index = self.broker_index

    def init_ui(self):


        header = ['Pair', 'timestamp', 'Bid 1', 'Ask 1', 'Bid 2', 'Ask 2', 'GAP',\
                  'POS', 'NEG', 'Offset', 'Spread 2']
        tbl_col_width = 100
        #Table
        self.tbl_viewResult = QTableWidget()
        self.tbl_viewResult.setColumnCount(len(header))
        self.tbl_viewResult.setRowCount(10)
        
        self.tbl_viewResult.setHorizontalHeaderLabels(header)
        self.tbl_viewResult.setColumnWidth(1, tbl_col_width)
        self.tbl_viewResult.setMinimumHeight(350)
        self.tbl_viewResult.setMinimumWidth(tbl_col_width * len(header))
        horHeader = self.tbl_viewResult.horizontalHeader()
        horHeader.setDefaultAlignment(Qt.AlignHCenter)

        self.timer = QTimer()

        self.btn_reset = QPushButton()
        self.btn_reset.setIcon(QIcon('img\\reset.png'))
        self.btn_reset.setIconSize(QSize(100, 100))
        self.btn_reset.setStatusTip('Reset the display')

        self.btnRun = QPushButton()
        self.btnRun.setIcon(QIcon('img\\run.png'))
        self.btnRun.setIconSize(QSize(100, 100))
        self.btnRun.setStatusTip('Run the Robot')

        self.btnStop = QPushButton()
        self.btnStop.setIcon(QIcon('img\\stop.png'))
        self.btnStop.setIconSize(QSize(100, 100))
        self.btnStop.setStatusTip('Stop the Robot')

        self.btn_closeAll = QPushButton()
        self.btn_closeAll.setIcon(QIcon('img\\close.png'))
        self.btn_closeAll.setIconSize(QSize(100, 100))
        self.btn_closeAll.setStatusTip('Close all open position')

        self.lbl_lot = QLabel()
        self.lbl_lot.setFont(QFont("Times", 12, QFont.Bold))

        self.btn_onOff = QLabel()
        self.btn_onOff.setPixmap(QPixmap('img\\off.png'))
        self.btn_onOff.setScaledContents(True)
        self.btn_onOff.setFixedSize(100,100)

        self.lbl_eaName = QLabel('High Frequency Trading Expert Advisor')
        self.lbl_eaName.setFont(QFont("Times", 20, QFont.Bold))
        self.lbl_eaName.setAlignment(Qt.AlignCenter)

        self.chk1_hedging = QCheckBox("Hedging")
        self.chk1_hedging.setStatusTip('Hedging for 2 Leg Arbitrage')
        self.chk1_hedging.setFont(QFont("Courier New", 12))

        self.chk2_saveData = QCheckBox("Save Data")
        self.chk2_saveData.setStatusTip('Save data to database')
        self.chk2_saveData.setFont(QFont("Courier New", 12))

        self.chk3_telegram = QCheckBox("Telegram")
        self.chk3_telegram.setStatusTip('Send notification to Telegram')
        self.chk3_telegram.setFont(QFont("Courier New", 12))

        self.lbl_verCheck = QLabel()
        self.lbl_verCheck.setFont(QFont("Times", 12, QFont.Bold))
        
        self.btn_master_broker = QPushButton()
        self.btn_master_broker.setFont(QFont("Courier New", 12))
        
        
        
        self.btn_brokers = []
        for b in range(len(slave_brokers)):
            self.btn_brokers.append(QPushButton())
            self.btn_brokers[b].setFont(QFont("Courier New", 12))
            
        self.chk_BrokSaveDB = []
        for k in range(len(slave_brokers)):
            self.chk_BrokSaveDB.append(QCheckBox('save'))
            self.chk_BrokSaveDB[k].setFont(QFont("Courier New", 13))
            
        self.lbl_errMsg = QLabel()
        self.lbl_errMsg.setFont(QFont("Times", 12, QFont.Bold))
        self.lbl_errMsg.setStyleSheet('color: red')
        
#        v4Sub_box = QVBoxLayout()
#        for lbl_broker in self.lbl_brokers:
#            v4Sub_box.addWidget(lbl_broker)
#        v4Sub_box.addStretch()

        v3Sub_box = QVBoxLayout()
        v3Sub_box.addWidget(self.chk3_telegram)
        v3Sub_box.addWidget(self.chk2_saveData)
        v3Sub_box.addWidget(self.chk1_hedging)
        v3Sub_box.addWidget(self.lbl_verCheck)
        v3Sub_box.addWidget(self.lbl_errMsg)
        v3Sub_box.addWidget(self.lbl_lot)
        v3Sub_box.addStretch()

        h3_box = QHBoxLayout()
        h3_box.addWidget(self.btnRun)
        h3_box.addWidget(self.btnStop)
        h3_box.addWidget(self.btn_reset)
        h3_box.addWidget(self.btn_closeAll)
#        h3_box.addLayout(v4Sub_box)
        h3_box.addStretch()
        h3_box.addWidget(self.btn_onOff)
        h3_box.addStretch()
        h3_box.addLayout(v3Sub_box)


        v_box = QVBoxLayout()
        v_box.addWidget(self.lbl_eaName)
        v_box.addStretch()
        v_box.addWidget(self.tbl_viewResult)
        v_box.addStretch()
        v_box.addLayout(h3_box)
        
        # ***************************************************
        # V2 Box
        v2_box = QVBoxLayout()
        
        lbl_empty = QLabel('Broker')
        lbl_empty.setFont(QFont("Times", 14, QFont.Bold))
        lbl_empty.setAlignment(Qt.AlignCenter)
        v2_box.addWidget(lbl_empty)
        
#        v4Sub_box = QVBoxLayout()
        v2_box.addWidget(self.btn_master_broker)
        for btn_broker in self.btn_brokers:
            v2_box.addWidget(btn_broker)
        v2_box.addStretch()
        
        # ***************************************************
        # V3 Box
        v3_box = QVBoxLayout()
        
        lbl_empty2 = QLabel('Database')
        lbl_empty2.setFont(QFont("Times", 14, QFont.Bold))
        lbl_empty2.setAlignment(Qt.AlignCenter)
        v3_box.addWidget(lbl_empty2)
        
        lbl_empty3 = QLabel('')
        lbl_empty3.setFont(QFont("Times", 20, QFont.Bold))
        lbl_empty3.setAlignment(Qt.AlignCenter)
        v3_box.addWidget(lbl_empty3)
        
        for chk_box in self.chk_BrokSaveDB:
            v3_box.addWidget(chk_box)
        v3_box.addStretch()
        
        
        
        # ***************************************************
        h_box_main = QHBoxLayout()
        h_box_main.addLayout(v2_box)
        h_box_main.addLayout(v3_box)
        h_box_main.addLayout(v_box)

#        self.setLayout(v_box)
        self.setLayout(h_box_main)

        #signal
        self.btnStop.clicked.connect(self.btn_Stop_pressed)
        self.btnRun.clicked.connect(self.btn_Run_pressed)
        self.btn_reset.clicked.connect(self.btn_reset_pressed)
        self.btn_closeAll.clicked.connect(self.btn_closeAll_pressed)        
        
#        self.broker_index = 1  #default value
#        self.btn_master_broker.clicked.connect(self.btn_master_pressed)
        
        for j in range(len(slave_brokers)): 
            self.btn_brokers[j].setCheckable(True)
            self.btn_brokers[j].clicked.connect(self.btn_broker_pressed)
#        
        
    def init_var(self):
        
        for slave in slave_brokers:
            slave.get_price()
            slave.limit_digit_dep()

    def btn_broker_pressed(self):
                             
#        print('change broker')
        cnt = 0
       
        for i in range(len(slave_brokers)):            
            
#            print('button ', i, self.btn_brokers[i].isChecked())
            if self.btn_brokers[i].isChecked():
                self.broker_index =i
                cnt += 1
            else:
                self.btn_brokers[i].setDisabled(True)
                
        if cnt == 0:
            for btn_bro in self.btn_brokers:
                btn_bro.setEnabled(True)
                
        global g_bro_index 
        g_bro_index = self.broker_index

#        print('broker index = ', self.broker_index)
            

    def chk_mqlVer(self):
        
        master_broker.get_acct_info()
        master_broker.get_zmq_ver()
        master_broker.init_symbol()
        
        for slave in slave_brokers:
            slave.get_acct_info()
            slave.get_zmq_ver()
            slave.init_symbol()
        
        if master_broker.zmq_mt4_ver == zmq_ver_cfg:
            print(master_broker.company, 'Zmq version check Pass')
        else:
            print(master_broker.company, 'Zmq version check Failed')
        
        for slave in slave_brokers:
            if slave.zmq_mt4_ver == zmq_ver_cfg:
                print(slave.company, 'Zmq version check Pass')
            else:
                print(slave.company, 'Zmq version check Failed')
        
#        if broker1.zmq_mt4_ver == zmq_ver_cfg  and broker2.zmq_mt4_ver == zmq_ver_cfg:
#            self.lbl_verCheck.setText('MQL Ver Pass')
#            self.lbl_verCheck.setStyleSheet('color: green')
#        else:
#            self.lbl_verCheck.setText('MQL Ver Fail')
#            self.lbl_verCheck.setStyleSheet('color: red')
#            self.btnRun.setDisabled(True)
#            
    def chk_broker_nm(self):

        self.btn_master_broker.setText(master_broker.company[:15])
        for b in range(len(slave_brokers)):
            self.btn_brokers[b].setText(slave_brokers[b].company[:15])

    def chk_initialization(self):

        if not cfgData.readStatus:
            self.lbl_errMsg.setText('Init Error')
            self.btnRun.setDisabled(True)
        
    def Widget_Init(self):
        self.btnRun.setEnabled(True)
        self.btnStop.setDisabled(True)
        self.btn_master_broker.setDisabled(True)
        self.broker_index = 0

    def btn_closeAll_pressed(self):
        print ('Close All Order for broker ', slave_brokers[self.broker_index].company)
        slave_brokers[self.broker_index].order_close_new(slave_brokers[self.broker_index].symbols)

    def btn_Run_pressed(self):
        
        if self.chk1_hedging.isChecked():
            print ('Run Arbitrage 2 Leg')
            self.timer.timeout.connect(self.run_2Leg_arb)
            self.timer.start(100)
        elif not self.chk1_hedging.isChecked():
            print ('Run Arbitrage 1 Leg')
            self.timer.timeout.connect(self.run_1Leg_arb)
            self.timer.start(100)
            
        self.btnRun.setDisabled(True)
        self.btnStop.setEnabled(True)
             

    def btn_Stop_pressed(self):
        print ('Stop Signal')
        self.btnRun.setEnabled(True)
        self.btnStop.setDisabled(True)
        self.btn_onOff.setPixmap(QPixmap('img\\off.png'))
        self.timer.stop()

    def btn_reset_pressed(self):
        print ('Reset Table')
        self.tbl_viewResult.clearContents()
        self.lbl_lot.setText('')
        
#This function is to execute 1 Leg arbitrage
    def run_1Leg_arb(self):
        
        #get all the info for master broker
        master_broker.get_price()
        master_broker.get_acct_info()
        master_broker.get_order_status()
        
        #get all the required info for slave broker
        for slave in slave_brokers:
            slave.get_price()
            slave.get_acct_info()
            slave.get_order_status()
            self.cal_gapPosNeg(master_broker, slave)
            self.cal_countArbitrage(master_broker,slave)
            slave.get_lots()
            
        #display Lot for next position if it get opened
        lot_text = 'Lot=' + str(slave_brokers[self.broker_index].lots)
        self.lbl_lot.setText(lot_text)
        
        master = master_broker
        slave = slave_brokers[self.broker_index]
        symbols = slave_brokers[self.broker_index].symbols
        gap = slave_brokers[self.broker_index].gap
        pos = slave_brokers[self.broker_index].pos
        neg = slave_brokers[self.broker_index].neg
        offset = slave_brokers[self.broker_index].offsets
        self.update_Table(master, slave, symbols, gap, pos, neg, offset)
        
        #save data to database
        if self.chk2_saveData.isChecked():
            self.save2DB()
        
        #look for signal amd trade
        for slave in slave_brokers:            

            #loop for each pair to trade
            for i in range(len(slave.symbols)):
    
                #calculate distance in pip for next level for entry
                next_step = slave.pip_step * (slave.trade_count[i] + 1)
    
                #check whether it is time NOT allowed to trade
                noTradeTime = vt.chk_OffTrade(start_day, start_time, end_day, end_time)
    
                preCheck = False    
                #check if timestamp for both broker is same and price NOT zero and there is connection for Broker 1 and 2
                if master_broker.tms == slave.tms and master_broker.bid[i] != 0 and slave.bid[i] != 0 and \
                    master_broker.connection and slave.connection:
                    preCheck = True
                   
    
                if preCheck and not noTradeTime and slave.balance <= max_profit:               
                    # set display button On/Off to ON
                    self.btn_onOff.setPixmap(QPixmap('img\\on.jpg'))
    
                    #exeute this logic if there is NO open position
                    if slave.trade_count[i] == 0:
    
                        #temporary disable comment to be untraceable
                        mt4_comments = ' '
    
                        # part 1 : if cnt arbitrage greather than cnt_arb_limit                       
                        if slave.cnt_arb[i] >= cnt_arb_limit:
    
                            #send BUY order
                            slave.send_order(BUY, slave.symbols[i], slave.ask[i], slave.lots, slave.SLIP, slave.stop_loss, mt4_comments)
                            print (slave.company, ': Open order buy for', slave.symbols[i])
    
                            #generate timestamp and remove milisecond
                            timestamp = str(datetime.now().replace(microsecond=0))
    
                            #generate text message for telegram
                            text_msg = timestamp + '\n' + slave.company + '\n' + slave.symbols[i] + ': Open position BUY' + '\n' + \
                                       'Pos =' +  str(slave.pos[i]) + '\n' + 'Gap =' + str(slave.gap[i])
    
                            #if telegram check box is selected, then send message to telegram
                            if self.chk3_telegram.isChecked():
                                bot.send_message(chat_id=chat_id, text=text_msg, timeout=50)
    
                            #save trade data to log file.
                            data = [slave.tms, slave.company, slave.symbols[i], slave.trade_count[i], master_broker.bid[i] \
                                    , master_broker.ask[i], slave.bid[i], slave.ask[i], 'BUY', 'level1', slave.pos[i] \
                                    , slave.cnt_arb[i]]
                            write_2_file(data)
    
                        #part 2 : if cnt arbitrage lesser than -cnt_arb_limit
                        elif slave.cnt_arb[i] <= - cnt_arb_limit:
    
                            #send SELL order
                            slave.send_order(SELL, slave.symbols[i], slave.bid[i], slave.lots, slave.SLIP, slave.stop_loss, mt4_comments)  # IC Market
                            print (slave.company, ': Open order sell for', slave.symbols[i])
    
                            # generate timestamp and remove milisecond
                            timestamp = str(datetime.now().replace(microsecond=0))
    
                            # generate text message for telegram
                            text_msg = timestamp + '\n' + slave.company + '\n' + slave.symbols[i] + ': Open position SELL' + '\n' + \
                                       'Neg =' + str(slave.neg[i]) + '\n' + 'Gap =' + str(slave.gap[i])
    
                            # if telegram check box is selected, then send message to telegram
                            if self.chk3_telegram.isChecked():
                                bot.send_message(chat_id=chat_id, text=text_msg, timeout=50)
                                
                            #save trade data to log file.
                            data = [slave.tms, slave.company, slave.symbols[i], slave.trade_count[i], master_broker.bid[i] \
                                    , master_broker.ask[i], slave.bid[i], slave.ask[i], 'SELL', 'level1', slave.neg[i] \
                                    , slave.cnt_arb[i]]
                            write_2_file(data)
    
                    # to close position if price converge again
                    elif slave.trade_count[i] > 0:
    
                        mt4_comments = ' '
                        # self.chk_hit_SL(symbols2[i],i)
    
                        if slave.order_type[i] == BUY and slave.pos[i] < slave.arbitrage_close and \
                            self.chk_closeValid(slave, slave.symbols[i]):
    
                            slave.order_close_new([slave.symbols[i]])
                            print (slave.company, ': Close order')
    
                            timestamp = str(datetime.now().replace(microsecond=0))
                            text_msg = timestamp + '\n' + slave.symbols[i] + ': Close position BUY'
                            if self.chk3_telegram.isChecked():
                                bot.send_message(chat_id=chat_id, text=text_msg, timeout=50)
    
                            data = [slave.tms, slave.company, slave.symbols[i], slave.trade_count[i], slave.bid[i], 'CLOSE']
                            write_2_file(data)
    
                        elif slave.order_type[i] == SELL and slave.neg[i] > -slave.arbitrage_close and \
                            self.chk_closeValid(slave, slave.symbols[i]):
    
                            slave.order_close_new([slave.symbols[i]])
                            print (slave.company, ': Close order')
    
                            timestamp = str(datetime.now().replace(microsecond=0))
                            text_msg = timestamp + '\n' + slave.symbols[i] + ': Close position SELL'
                            if self.chk3_telegram.isChecked():
                                bot.send_message(chat_id=chat_id, text=text_msg, timeout=50)
    
                            data = [slave.tms, slave.company, slave.symbols[i], slave.trade_count[i], slave.ask[i], 'CLOSE']
                            write_2_file(data)
    
                        
                        # open layer if price gap further
    
                        elif slave.order_type[i] == BUY and slave.pos[i] >= next_step and slave.cnt_arb[i] >= cnt_arb_limit:
    
                            slave.send_order(BUY, slave.symbols[i], slave.ask[i], slave.lots, slave.SLIP, slave.stop_loss, mt4_comments)  # IC Market
                            print (slave.company, ': Open order buy for next lvl ', slave.symbols[i])
    
                            timestamp = str(datetime.now().replace(microsecond=0))
                            text_msg = timestamp + '\n' + slave.symbols[i] + ': Open position BUY for next level' + '\n' + mt4_comments
                            if self.chk3_telegram.isChecked():
                                bot.send_message(chat_id=chat_id, text=text_msg, timeout=50)
                                
                            #save trade data to log file.
                            data = [slave.tms, slave.company , slave.symbols[i], slave.trade_count[i], master_broker.bid[i] \
                                    , master_broker.ask[i], slave.bid[i], slave.ask[i], 'BUY', 'Next level', slave.neg[i] \
                                    , slave.cnt_arb[i]]
                            write_2_file(data)
    
                        elif slave.order_type[i] == SELL and slave.neg[i] <= - next_step and slave.cnt_arb[i] <= -cnt_arb_limit:
    
                            slave.send_order(SELL, slave.symbols[i], slave.bid[i], slave.lots, slave.SLIP, slave.stop_loss, mt4_comments)  # IC Market
                            print (slave.company, ': Open order sell for next lvl ', slave.symbols[i])
    
                            timestamp = str(datetime.now().replace(microsecond=0))
                            text_msg = timestamp + '\n' + slave.symbols[i] + ': Open position SELL for next level' + '\n' + mt4_comments
                            if self.chk3_telegram.isChecked():
                                bot.send_message(chat_id=chat_id, text=text_msg, timeout=50)
                                
                            #save trade data to log file.
                            data = [slave.tms, slave.company, slave.symbols[i], slave.trade_count[i], master_broker.bid[i] \
                                    , master_broker.ask[i], slave.bid[i], slave.ask[i], 'SELL', 'Next level', slave.neg[i] \
                                    , slave.cnt_arb[i]]
                            write_2_file(data)
    
    
                else:
                    self.btn_onOff.setPixmap(QPixmap('img\\off.png'))
    
                    # to close position if price converge again
                    if slave.trade_count[i] > 0 and preCheck:
    
                        if slave.order_type[i] == BUY and slave.pos[i] < slave.arbitrage_close \
                        and self.chk_closeValid(slave, slave.symbols[i]):
                                                            
                            slave.order_close_new([slave.symbols[i]])
                            print (slave.company, ': Close order')
    
                            timestamp = str(datetime.now().replace(microsecond=0))
                            text_msg = timestamp + '\n' + slave.symbols[i] + ': Close position BUY'
                            bot.send_message(chat_id=chat_id, text=text_msg, timeout=50)
    
                            data = [slave.tms, slave.company, slave.symbols[i], slave.trade_count[i], slave.bid[i], 'CLOSE']
                            write_2_file(data)
    
                        elif slave.order_type[i] == SELL and slave.neg[i] > -slave.arbitrage_close \
                        and self.chk_closeValid(slave, slave.symbols[i]):
                            
                            slave.order_close_new([slave.symbols[i]])
                            print (slave.company, ': Close order')
    
                            timestamp = str(datetime.now().replace(microsecond=0))
                            text_msg = timestamp + '\n' + slave.symbols[i] + ': Close position SELL'
                            bot.send_message(chat_id=chat_id, text=text_msg, timeout=50)
                            
                            data = [slave.tms, slave.company, slave.symbols[i], slave.trade_count[i], slave.ask[i], 'CLOSE']
                            write_2_file(data)
    
    def save2DB(self):
        
        #if data with new timestamp then set to turn ON Save data
        if master_broker.tms > self.previous_tms:
                        
            self.previous_tms = master_broker.tms
                
            #save data for master
            for i in range(len(master_broker.symbols)):
                db.save2db(database, master_broker.tms, master_broker.company, \
                           master_broker.symbols[i], master_broker.digits[i], \
                           master_broker.bid[i], master_broker.ask[i])
            
            #save data for slave
            for j in range(len(slave_brokers)):
                
                if self.chk_BrokSaveDB[j].isChecked():
                    
                    for i in range(len(slave_brokers[j].symbols)):
                        db.save2db(database, slave_brokers[j].tms, slave_brokers[j].company, \
                           slave_brokers[j].symbols[i], slave_brokers[j].digits[i], slave_brokers[j].bid[i], \
                           slave_brokers[j].ask[i])
                    
                        
    def chk_closeValid(self, broker, symbol):
        closeValid = False

        openTime, mt4ServerTime = broker.get_openTime(symbol)
        allowedCloseTime = openTime + dt.timedelta(seconds= scalpingRuleTime)

        if mt4ServerTime > allowedCloseTime:
                closeValid=True

        return closeValid

    def cal_gapPosNeg(self, master, slave):
        
        for i in range(len(pairs)):

            if master.digits[i] < slave.digits[i]:
                digits = master.digits[i]
            else:
                digits = slave.digits[i]
            
            slave.gap[i] = round((master.avg_price[i] - slave.avg_price[i]) * math.pow(10, digits), 1) + slave.offsets[i]
            slave.pos[i] = round((master.bid[i] - slave.ask[i]) * math.pow(10, digits), 1) + slave.offsets[i]
            slave.neg[i] = round((master.ask[i] - slave.bid[i]) * math.pow(10, digits), 1) + slave.offsets[i]
            
        

    # This function is to assign number of arbitrage that continously counted
    # to ensure it happended more than 1 sec 
    def cal_countArbitrage(self, master, slave):

       
        #iterate based on how many pair traded
        for i in range(len(pairs)):

            # check if timestamp for both broker is same and price NOT zero and there is connection for Broker 1 and 2
            if master.tms == slave.tms and master.bid[i] != 0 and slave.bid[i] != 0 and \
                    master.connection and slave.connection :

                #increase arbitrage count if encounter positive arbitrage
                if slave.pos[i] >= slave.arbitrage_open:
                    slave.cnt_arb[i] += 1

                #decrease arbitrage count if encounter negative arbitrage
                elif slave.neg[i] <= -slave.arbitrage_open:
                    slave.cnt_arb[i] -= 1
                    
                #reset the cnt_arb to zero if no more negative arbitrage
                else:
                    slave.cnt_arb[i] = 0 
                    
        
    

    def update_Table(self, master, slave, symbols, gap, pos, neg, offset):
        
        
#        s_digit = slave.digits
        for i in range(len(symbols)):
            
            m_fmt = "{0:0."+str(master.digits[i])+"f}"
            s_fmt = "{0:0."+str(slave.digits[i])+"f}"
            gap_fmt = "{0:0.1f}"
#            print('master format',m_fmt)
            
#            self.tbl_viewResult.setItem(i, 0, QTableWidgetItem(symbols[i][:6]))
            self.tbl_viewResult.setItem(i, 0, QTableWidgetItem(symbols[i]))
            self.tbl_viewResult.setItem(i, 1, QTableWidgetItem(str(master.tms.time())))
            self.tbl_viewResult.setItem(i, 2, QTableWidgetItem(m_fmt.format(master.bid[i])))
            self.tbl_viewResult.setItem(i, 3, QTableWidgetItem(m_fmt.format(master.ask[i])))
            self.tbl_viewResult.setItem(i, 4, QTableWidgetItem(s_fmt.format(slave.bid[i])))
            self.tbl_viewResult.setItem(i, 5, QTableWidgetItem(s_fmt.format(slave.ask[i])))
#            self.tbl_viewResult.setItem(i, 6, QTableWidgetItem(m_fmt.format(master.avg_price[i])))
#            self.tbl_viewResult.setItem(i, 7, QTableWidgetItem(s_fmt.format(slave.avg_price[i])))
            self.tbl_viewResult.setItem(i, 6, QTableWidgetItem(gap_fmt.format(gap[i])))
            self.tbl_viewResult.setItem(i, 7, QTableWidgetItem(gap_fmt.format(pos[i])))
            self.tbl_viewResult.setItem(i, 8, QTableWidgetItem(gap_fmt.format(neg[i])))
            self.tbl_viewResult.setItem(i, 9, QTableWidgetItem(gap_fmt.format(offset[i])))
            self.tbl_viewResult.setItem(i, 10, QTableWidgetItem(gap_fmt.format(slave.spread[i])))

        self.tbl_viewResult.repaint()

    def chk_hit_SL(self, symbol, index):

        count, order_type, price = broker2.get_open_price(symbol)

        if broker1.digits[index] < broker2.digits[index]:
            digits = broker1.digits[index]
        else:
            digits = broker2.digits[index]

        if count > 0 and stop_loss != 0:
            for i in len(price):

                if order_type == BUY:
                    gap = price[i] - broker2.bid
                    gap_pip = round( gap * math.pow(10, digits), 1)

                if order_type == SELL:
                    gap = broker2.ask - price[i]
                    gap_pip = round(gap * math.pow(10, digits), 1)

                if gap_pip >= stop_loss:
                    broker2.order_close_new([symbol])
                    print ('broker 2: Hit Stop Loss')

                    timestamp = str(datetime.now().replace(microsecond=0))
                    text_msg = timestamp + '\n' + symbols2[i] + ': Hit Stop Loss'
                    if self.chk3_telegram.isChecked():
                        bot.send_message(chat_id=chat_id, text=text_msg, timeout=50)

                    data = [broker2.tms, symbols2[i], broker2.trade_count[i], broker2.ask[i], 'StopLoss']
                    write_2_file(data)

class TestWindow(QMainWindow):
    def __init__(self, parent=None):
        super(TestWindow, self).__init__(parent)
        self.test_widget = TestWidget(self)
        self.setCentralWidget(self.test_widget)
        

        self.setWindowTitle('Test Mode')
        self.setGeometry(200, 200, 600, 400)

class TestWidget(QWidget):
    def __init__(self, parent):
        super(TestWidget, self).__init__(parent)
        self.setFixedSize(650,550)
        self.init_ui()
#        self.broker_index = form_widget.broker_index
#        self.broker_index = FormWidget.broker_index

    def init_ui(self):

        btn_width = 70
        btn_height = 70

        self.btn_sendOrder = QPushButton('Send Order')
        self.btn_sendOrder.setFixedWidth(btn_width)
        self.btn_sendOrder.setFixedHeight(btn_height)

        self.btn_closeSingle = QPushButton('Close')
        self.btn_closeSingle.setFixedWidth(btn_width)
        self.btn_closeSingle.setFixedHeight(btn_height)

        self.btn_closeAll = QPushButton('Close All')
        self.btn_closeAll.setFixedWidth(btn_width)
        self.btn_closeAll.setFixedHeight(btn_height)

        self.btn_sendTelegram = QPushButton('Telegram')
        self.btn_sendTelegram.setFixedWidth(btn_width)
        self.btn_sendTelegram.setFixedHeight(btn_height)

        self.btn_getPrice = QPushButton('Get Price')
        self.btn_getPrice.setFixedWidth(btn_width)
        self.btn_getPrice.setFixedHeight(btn_height)

        self.btn_reset = QPushButton('Reset')
        self.btn_reset.setFixedWidth(btn_width)
        self.btn_reset.setFixedHeight(btn_height)

        self.btn_excel = QPushButton('Export CSV')
        self.btn_excel.setFixedWidth(btn_width)
        self.btn_excel.setFixedHeight(btn_height)

        v1_box = QVBoxLayout()
        v1_box.addWidget(self.btn_sendOrder)
        v1_box.addWidget(self.btn_closeSingle)
        v1_box.addWidget(self.btn_closeAll)
        v1_box.addWidget(self.btn_sendTelegram)
        v1_box.addWidget(self.btn_getPrice)
        v1_box.addWidget(self.btn_reset)
        v1_box.addWidget(self.btn_excel)
        v1_box.addStretch()

        self.lbl_symbol = QLabel('Symbol : ')
        self.lbl_symbol.setFont(QFont("Courier New", 12))

        self.txt_symbol = QLineEdit(self)
        self.txt_symbol.setFont(QFont("Courier New", 12))
        self.txt_symbol.setFixedWidth(450)

        self.txt_promt = QTextEdit(self)
        self.txt_promt.setFixedWidth(550)
        self.txt_promt.setFixedHeight(450)
        self.txt_promt.setFont(QFont("Courier New", 12))
        self.txt_promt.setAlignment(Qt.AlignTop)
        # self.txt_promt.setAlignment(Qt.AlignJustify)


        self.chk_broker1 = QCheckBox("Broker 1")
        self.chk_broker1.setFont(QFont("Courier New", 12))

        self.chk_broker2 = QCheckBox("Broker 2")
        self.chk_broker2.setFont(QFont("Courier New", 12))

        self.chk_query = QCheckBox("Custom Query")
        self.chk_query.setFont(QFont("Courier New", 12))


        h0_sub_box = QHBoxLayout()
        h0_sub_box.addWidget(self.lbl_symbol)
        h0_sub_box.addWidget(self.txt_symbol)
        h0_sub_box.addStretch()

        h1_sub_box = QHBoxLayout()
        h1_sub_box.addWidget(self.chk_broker1)
        h1_sub_box.addWidget(self.chk_broker2)
        h1_sub_box.addStretch()
        h1_sub_box.addWidget(self.chk_query)

        v2_box = QVBoxLayout()
        v2_box.addLayout(h0_sub_box)
        v2_box.addStretch()
        v2_box.addLayout(h1_sub_box)
        v2_box.addStretch()
        v2_box.addWidget(self.txt_promt)
        v2_box.addStretch()

        h_box = QHBoxLayout()
        h_box.addLayout(v1_box)
        h_box.addLayout(v2_box)

        self.btn_sendTelegram.clicked.connect(self.btn_telegram_pressed)
        self.btn_sendOrder.clicked.connect(self.btn_sendOrder_pressed)
        self.btn_closeSingle.clicked.connect(self.btn_closeSingle_pressed)
        self.btn_closeAll.clicked.connect(self.btn_closeAll_pressed)
        self.btn_getPrice.clicked.connect(self.btn_getPrice_pressed)
        self.btn_reset.clicked.connect(self.btn_reset_pressed)
        self.btn_excel.clicked.connect(lambda:self.btn_excel_pressed(self.chk_query))
        self.chk_query.stateChanged.connect(lambda:self.chk_query_changed(self.chk_query))

        self.setLayout(h_box)

    def chk_query_changed(self,q):

        sql =  ''' select price_id, date(timestamp),time(timestamp), broker_nm, symbol, digits, bid, ask
        from price inner join broker on price.broker_id = broker.broker_id
        inner join attribute on price.attrib_id = attribute.attrib_id '''


        if q.isChecked():
            self.txt_promt.setText(sql)
        else:
            self.txt_promt.clear()

    def btn_telegram_pressed(self):
        print ('Send telegram message: debug mode')
        timestamp = str(datetime.now().replace(microsecond=0))
        text_msg = timestamp + '\n' + 'test message sent from EA'
        bot.send_message(chat_id=chat_id, text=text_msg, timeout=50)

    def btn_sendOrder_pressed(self):
        
        self.broker_index = g_bro_index
        print ('Send Order')
        selSymbols = str(self.txt_symbol.text())
        selSymbols = selSymbols.replace(' ', '')
        selSymbols = selSymbols.split(',')

        selSymbols1 = []
        selSymbols2 = []
        symbol_index = None

        for symbol in selSymbols:
            sym1 = symbol + master_suffix
            sym2 = symbol + slave_suffixs[self.broker_index]
            selSymbols1.append(sym1)
            selSymbols2.append(sym2)

        if self.chk_broker1.isChecked() and not self.chk_broker2.isChecked():
#            master_broker.get_price(selSymbols1)
            master_broker.get_price()

            for s in range(len(selSymbols1)):
                master_broker.send_order(BUY, selSymbols1[s], master_broker.ask[s], LOTS, SLIP_param, stop_loss_param, 'test')
                master_broker.send_order(SELL, selSymbols1[s], master_broker.bid[s], LOTS, SLIP_param, stop_loss_param, 'test')

        elif not self.chk_broker1.isChecked() and self.chk_broker2.isChecked():
            slave_brokers[self.broker_index].get_price()
#            print('okay 1 ')

            for pair in selSymbols2:
#                print('okay 2')
                
                
                for j in range(len(slave_brokers[self.broker_index].symbols)):
                    if pair == slave_brokers[self.broker_index].symbols[j]:
                        symbol_index = j
                        break
#                print('okay 3', 'symbol index =', symbol_index)
                
                slave_brokers[self.broker_index].send_order(BUY, pair, slave_brokers[self.broker_index].ask[symbol_index] \
                             ,LOTS, slave_brokers[self.broker_index].SLIP, slave_brokers[self.broker_index].stop_loss, 'test')
                slave_brokers[self.broker_index].send_order(SELL, pair, slave_brokers[self.broker_index].bid[symbol_index] \
                             ,LOTS, slave_brokers[self.broker_index].SLIP, slave_brokers[self.broker_index].stop_loss,'test')

        elif self.chk_broker1.isChecked() and self.chk_broker2.isChecked():
            master_broker.get_price()
            slave_brokers[self.broker_index].get_price()

            for s in range(len(selSymbols1)):
                master_broker.send_order(BUY, selSymbols1[s], master_broker.ask[s], LOTS\
                                         , SLIP_param, stop_loss_param, 'test')
                master_broker.send_order(SELL, selSymbols1[s], master_broker.bid[s], LOTS\
                                         , SLIP_param, stop_loss_param, 'test')
                slave_brokers[self.broker_index].send_order(BUY, selSymbols2[s], slave_brokers[self.broker_index].ask[s]\
                             , LOTS, slave_brokers[self.broker_index].SLIP, slave_brokers[self.broker_index].stop_loss, 'test')
                slave_brokers[self.broker_index].send_order(SELL, selSymbols2[s], slave_brokers[self.broker_index].bid[s]\
                             , LOTS, slave_brokers[self.broker_index].SLIP, slave_brokers[self.broker_index].stop_loss, 'test')

    def btn_closeSingle_pressed(self):
        print ('Close selected pair(s)')
        selSymbols = str(self.txt_symbol.text())
        selSymbols = selSymbols.replace(' ', '')
        selSymbols = selSymbols.split(',')

        selSymbols1 = []
        selSymbols2 = []

        for symbol in selSymbols:
            sym1 = symbol + suffix_bro1
            sym2 = symbol + suffix_bro2
            selSymbols1.append(sym1)
            selSymbols2.append(sym2)

        if self.chk_broker1.isChecked() and not self.chk_broker2.isChecked():
            broker1.order_close_new(selSymbols1)
        elif not self.chk_broker1.isChecked() and self.chk_broker2.isChecked():
            broker2.order_close_new(selSymbols2)
        elif self.chk_broker1.isChecked() and self.chk_broker2.isChecked():
            broker1.order_close_new(selSymbols1)
            broker2.order_close_new(selSymbols2)

    def btn_closeAll_pressed(self):
        print ('Close All Order')
        broker1.order_close_new(symbols1)
        broker2.order_close_new(symbols2)

    def btn_getPrice_pressed(self):
        print ('Get Quotes')
        broker1.get_price(symbols1)
        broker2.get_price(symbols2)
        FormWidget.cal_gapPosNeg()

        FormWidget.update_Table(symbols1)

    def btn_reset_pressed(self):
        print ('Reset Screen')
        self.txt_symbol.clear()
        self.txt_promt.clear()
        self.chk_broker1.setChecked(False)
        self.chk_broker2.setChecked(False)
        self.chk_query.setChecked(False)

    def btn_excel_pressed(self,q):

        sql = str(self.txt_promt.toPlainText())
        print (sql)

        if q.isChecked():
            db.exportCustom(database, csv_filename, sql)
        else:
            db.export2excel(database, csv_filename)

        print ('export data to CSV successful !!!')


# Function to send commands to ZeroMQ MT4 EA
def remote_send(socket, data):

    msg = None
    try:

        socket.send_string(data)
        msg = socket.recv_string()

    except zmq.Again as e:
        print ("1.Waiting for PUSH from MetaTrader 4.. :", e)
#        sleep(1)

# Function to retrieve data from ZeroMQ MT4 EA
def remote_pull(socket):

    msg = None
    try:
        msg = socket.recv_string()
    # msg = socket.recv(flags=zmq.NOBLOCK)

    except zmq.Again as e:
        print ("2.Waiting for PUSH from MetaTrader 4.. :", e)
#        sleep(1)

    return msg

class broker_class:
    tms = None
    trade_count = None
    err_msg = None
    req_socket = None
    pull_socket = None
    symbol = None
    magic_number = None

    def __init__(self, broker, magic_no, symb, offsets = None):       
        self.get_socket(broker)      
        self.magic_number = magic_no
        self.var_initialization(symb, offsets)

        
    def var_initialization(self, symb, offsets):
        self.pos = []
        self.neg = []
        self.gap = []        
        self.cnt_arb = []
        self.symbols = []
        self.offsets = []
        
        
        for i in range(len(pairs)):
            self.pos.append(0.0)
            self.neg.append(0.0)
            self.gap.append(0.0)
            self.cnt_arb.append(0)
            self.symbols.append(symb[i])      
            
        if offsets != None:
            for offset in offsets:
                self.offsets.append(offset)
                
    #To initialize limit that depend on broker digits            
    def limit_digit_dep(self):
        
        if self.digits == 2 or self.digits == 4:
            self.arbitrage_open = arbitrage_open_param / 10
            self.arbitrage_close = arbitrage_close_param /10
            self.pip_step = pip_step_param /10
            self.SLIP = SLIP_param /10
            self.stop_loss = stop_loss_param /10
                            
        else:
            self.arbitrage_open = arbitrage_open_param
            self.arbitrage_close = arbitrage_close_param
            self.pip_step = pip_step_param
            self.SLIP = SLIP_param
            self.stop_loss = stop_loss_param
                        

    def get_socket(self, broker):
        context = zmq.Context()

        socket_req = broker + ':5555'
        socket_pull = broker + ':5556'

        # Create REQ Socket
        reqSocket = context.socket(zmq.REQ)
        reqSocket.connect(socket_req)
        self.req_socket = reqSocket

        # Create PULL Socket
        pullSocket = context.socket(zmq.PULL)
        pullSocket.connect(socket_pull)
        self.pull_socket = pullSocket

    def get_price(self):

        sym = ''
        for symbol in self.symbols:
            sym = sym + '|' + symbol

        # print sym
        get_rates = "RATES"+ sym
        # print get_rates

        remote_send(self.req_socket, get_rates)
        msg = remote_pull(self.pull_socket)

        self.bid = []
        self.ask = []
        self.spread = []
        self.digits = []
        self.avg_price = []
        for i in range(len(symbols)):
            self.bid.append(0.0)
            self.ask.append(0.0)
            self.spread.append(0.0)
            self.digits.append(0)
            self.avg_price.append(0.0)

        # print msg
        if msg is not None:
            quote = msg.split('|')
            self.tms =  datetime.strptime(quote[0], '%Y.%m.%d %H:%M:%S')

            for i in range(len(symbols)):
                self.bid[i] = float(quote[(i*4)+1])
                self.ask[i] = float(quote[(i*4)+2])
                self.spread[i] = float(quote[(i*4)+3])
                self.digits[i] = int(float(quote[(i*4)+4]))
                self.avg_price[i] = round((self.bid[i] + self.ask[i])/2,self.digits[i])
            # print i

            # print self.bid, self.ask, self.avg_price

    def get_count(self, symbols):

        sym = ''
        for s in symbols:
            sym = sym + '|' + s

        self.trade_count =[]
        for a in range(len(symbols)):
            self.trade_count.append(0)

        req_count = "COUNT|"+ str(self.magic_number) + sym

        remote_send(self.req_socket, req_count)
        msg = remote_pull(self.pull_socket)

        # msg = 'COUNT|1|2|3|4|5|6'
        # print msg

        if msg is not None:
            quote = msg.split('|')
            for i in range(len(symbols)):
                # print i, '\t', quote[i + 1]
                self.trade_count[i] = int(float(quote[i+1]))

            # print self.trade_count

    def get_openTime(self, symbol):

        lastOpenTime = None
        mt4ServerTime = None
        req_OpenTime = "LASTOPENTIME|" + str(self.magic_number) + "|" + symbol

        remote_send(self.req_socket, req_OpenTime)
        msg = remote_pull(self.pull_socket)

        if msg is not None:
            quote = msg.split('|')
            lastOpenTime = datetime.strptime(quote[0], '%Y.%m.%d %H:%M:%S')
            mt4ServerTime = datetime.strptime(quote[1], '%Y.%m.%d %H:%M:%S')

        return  lastOpenTime, mt4ServerTime

    #this function will return trade count, order type  and  last price
    def get_order_status(self):
        sym = ''
        for symbol in self.symbols:
            sym = sym + '|' + symbol

        get_status = "STATUS|" + str(self.magic_number) + sym
        # print get_status

        remote_send(self.req_socket, get_status)
        msg = remote_pull(self.pull_socket)

        # print msg

        self.trade_count = []
        self.order_type = []
        self.last_price = []
        for i in range(len(symbols)):
            self.trade_count.append(0.0)
            self.order_type.append(None)
            self.last_price.append(0.0)

        # print msg
        if msg is not None:
            quote = msg.split('|')

            for i in range(len(symbols)):
                self.trade_count[i] = int(float(quote[(i * 3) + 0]))
                self.order_type[i] = int(float(quote[(i * 3) + 1]))
                self.last_price[i] = float(quote[(i * 3) + 2])

            # print self.trade_count, self.order_type, self.last_price

    #this function will return trade count, order type  and  last price
    def get_open_price(self, symbol):

        get_price = "OPENPRICE|" + str(self.magic_number) + symbol
        # print get_status

        remote_send(self.req_socket, get_price)
        msg = remote_pull(self.pull_socket)

        # print msg

        trade_count = 0
        order_type = None
        price = []

        # print msg
        if msg is not None:
            quote = msg.split('|')
            trade_count = int(float(quote[0]))
            order_type = quote[1]
            for i in range(trade_count):
                price.append(quote[1+i])

        return trade_count, order_type, price



    def get_profit(self, symbols):

        sym = ''
        for s in symbols:
            sym = sym + '|' + s

        self.profit =[]
        for a in range(len(symbols)):
            self.profit.append(0.0)

        req_count = "PROFIT|"+ str(self.magic_number) + sym

        print (req_count)
        remote_send(self.req_socket, req_count)
#        sys.exit()

        msg = remote_pull(self.pull_socket)

        print (msg)

        if msg is not None:
            quote = msg.split('|')
            for i in range(len(symbols)):
                # print i, '\t', quote[i + 1]
                self.profit[i] = int(float(quote[i+1]))

        print (self.profit)

    def send_order(self, order_type, symbol, price, lot=0.01, slip=10, stop_loss=0, comments="no comments"):

        #format 'TRADE|OPEN|ordertype|symbol|openprice|lot|SL|TP|Slip|comments|magicnumber'

        order = "TRADE|OPEN|"+ str(order_type)+"|" + symbol +"|"+ str(price)+"|"+ str(lot)+ "|" + str(stop_loss)+ "|0|" + str(slip)+"|"+comments +"|"+str(self.magic_number)
        print (order)

        remote_send(self.req_socket, order)
    # msg = remote_pull(self.pull_socket)

    def order_close_new(self, symbols):

        str_symb = ''
        # print symbols
        for s in symbols:
            str_symb = str_symb +'|' + s
        # print str_symb

        # format 'TRADE|CLOSE|magicnumber|symbol1, symbol2, ..'
        close_order = 'TRADE|CLOSE|'+ str(self.magic_number) + str_symb

        print (close_order)
        # sys.exit()

        remote_send(self.req_socket, close_order)

    def get_zmq_ver(self):

        chk_ver = 'EAVERSION'
        print ('Check ZMQ version')
        remote_send(self.req_socket, chk_ver)
        msg = remote_pull(self.pull_socket)

        self.zmq_mt4_ver = msg

    def get_acct_info(self):

        acct_info = 'ACCTINFO'
        # print 'Check account info'
        remote_send(self.req_socket, acct_info)
        msg = remote_pull(self.pull_socket)
        # print msg

        if msg is not None:
            quote = msg.split('|')
            self.company = quote[0]
            self.acctName = quote[1]
            self.acctNumber = int(float(quote[2]))
            self.balance = float(quote[3])
            self.profit = float(quote[4])

            if quote[5] == 'true' or quote[5] == 'True':
                self.connection = True
            else:
                self.connection = False

    def init_symbol(self):

        str_symb = ''
        for s in self.symbols:
            str_symb = str_symb + '|' + s

        init_symbols = 'INITIALIZE' + str_symb
        print ('Initialize MT4 Symbols ...')

        remote_send(self.req_socket, init_symbols)

    def get_lots(self):
        self.lots = 0.0

        #----------------------
        if minLOT == 0.01:
            rounders = 2
        elif minLOT == 0.1:
            rounders = 1
        else:
            rounders = 0

        #------------------------
        if RISK == 'HIGH':
            pipRisk = 200
        elif RISK == 'MEDIUM':
            pipRisk = 500
        elif RISK == 'LOW':
            pipRisk = 1000

        #----------------------------
        if RISK != 'manual':
            usdPerPip = self.balance / pipRisk
            self.lots = round((usdPerPip / lot2usd_ratio),rounders)
        elif RISK == 'manual':
            self.lots = LOTS

        

def write_2_file(data_2_write):
    with open(filename, 'a') as f:
        writer = csv.writer(f)
        writer.writerow(data_2_write)
    f.close()

# Run Tests -----------------------------------------------------------
print ('PROGRAM START')

bot = telegram.Bot(token= token)

master_symbol = []
for pair in pairs:
    master_symbol.append(pair + master_suffix)

slave_symbols=[]
for suffix in slave_suffixs:
    symbols = []
    for pair in pairs:
        symbols.append(pair + suffix)
    slave_symbols.append(symbols)

master_broker = broker_class('tcp://' + master_ip, magic_number, master_symbol)
slave_brokers = []
for i in range(len(slave_ips)):
    ip = 'tcp://' + slave_ips[i]
    slave_brokers.append(broker_class(ip, magic_number, slave_symbols[i], gaps_offsets[i]))

#update  offset in dataframe

        
    

#master_broker.get_acct_info()
#print(master_broker.company)
#slave_brokers[3].get_acct_info()
#print(slave_brokers[3].company)
#print(master_symbol)
#print(master_broker.symbols)
#print(slave_brokers[0].symbols)
    
#import sys
#sys.exit()

#Parameters
BUY = 0
SELL = 1

#------------------------ write to log file -------------
# ['timestamp', 'symbol', 'countTrade', entry_price, broker1_bid, broker1_ask, broker2_bid, \
# broker2_ask, 'tradeType', 'level', 'posNeg', 'cnt_arb']
directory = 'data'
filename = directory + '\\' + 'arbitrage.log'
header= ['timestamp', 'symbol', 'countTrade', 'entry_price', 'broker1_bid', 'broker1_ask', 'broker2_bid', \
         'broker2_ask', 'tradeType', 'level', 'posNeg', 'cnt_arb']

if not os.path.exists(directory):
    os.makedirs(directory)

if not os.path.exists(filename) :
    write_2_file(header)


#------------------------ write to database -------------
db_dir = 'database'
database = db_dir + '\\' + 'si.db'
csv_filename = db_dir + '\\' + 'data.csv'

if not os.path.exists(db_dir):
    os.makedirs(db_dir)

#------------------- main program ----------------
app = QApplication([])
superIpin = MyMainWindow()
superIpin.show()
sys.exit(app.exec_())
