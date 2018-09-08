'''
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
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import telegram
import csv
import ReadConfig
import validateTime as vt
import write2db as db

app_name = 'SuperIpin 10.5a'
ea_name_ver = 'SuperIpin 10.4a'
zmq_ver_cfg = 'zeromq_10.0'
cfgData = ReadConfig.config('superipin.cfg')
# print 'cfgData result =',cfgData.readStatus

#Read from config file
# ----------------------------------------------
ip_1 = 'tcp://'+ cfgData.ip1
ip_2 = 'tcp://'+ cfgData.ip2
magic_number = cfgData.magic_number
SLIP = cfgData.SLIP
LOTS = cfgData.LOTS
RISK = cfgData.risk
minLOT = cfgData.min_lot
lot2usd_ratio = cfgData.lot2usd_ratio
pairs = cfgData.symbols
gaps_offset = cfgData.gap_offset
suffix_bro1 = cfgData.suffix_bro1
suffix_bro2 = cfgData.suffix_bro2
arbitrage_open = cfgData.arbitrage_open
arbitrage_close = cfgData.arbitrage_close
pip_step = cfgData.pip_step
chat_id = cfgData.chat_id
token = cfgData.token
scalpingRuleTime = cfgData.scalping_rule
comments = cfgData.comments
start_day = cfgData.start_day
start_time = cfgData.start_time
end_day = cfgData.end_day
end_time = cfgData.end_time
max_profit = cfgData.max_profit
stop_loss = cfgData.stop_loss



class MyMainWindow(QMainWindow):

    def __init__(self, symbols1,symbols2, parent=None):

        super(MyMainWindow, self).__init__(parent)
        self.form_widget = FormWidget(self)
        self.setCentralWidget(self.form_widget)

        self.setWindowIcon(QIcon('img\\ipin.png'))
        self.setWindowTitle(app_name)
        self.setGeometry(150, 150, 1300, 550)

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
        print 'Enter Test Mode'
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

    def init_ui(self):


        #Table
        self.tbl_viewResult = QTableWidget()
        self.tbl_viewResult.setColumnCount(12)
        self.tbl_viewResult.setRowCount(10)
        header = ['Pair', 'timestamp', 'Bid 1', 'Ask 1', 'Bid 2', 'Ask 2', 'PriceAvg 1', 'PriceAvg 2', 'GAP', 'POS',
                  'NEG', 'Offset']
        self.tbl_viewResult.setHorizontalHeaderLabels(header)
        self.tbl_viewResult.setColumnWidth(1, 150)
        self.tbl_viewResult.setMinimumHeight(350)
        self.tbl_viewResult.setMinimumWidth(1250)
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

        self.chk1 = QCheckBox("Hedging")
        self.chk1.setStatusTip('Hedging for 2 Leg Arbitrage')
        self.chk1.setFont(QFont("Courier New", 12))

        self.chk2_saveData = QCheckBox("Save Data")
        self.chk2_saveData.setStatusTip('Save data to database')
        self.chk2_saveData.setFont(QFont("Courier New", 12))

        self.chk3_telegram = QCheckBox("Telegram")
        self.chk3_telegram.setStatusTip('Send notification to Telegram')
        self.chk3_telegram.setFont(QFont("Courier New", 12))

        self.lbl_verCheck = QLabel()
        self.lbl_verCheck.setFont(QFont("Times", 12, QFont.Bold))

        self.lbl_errMsg = QLabel()
        self.lbl_errMsg.setFont(QFont("Times", 12, QFont.Bold))
        self.lbl_errMsg.setStyleSheet('color: red')


        v3Sub_box = QVBoxLayout()
        v3Sub_box.addWidget(self.chk3_telegram)
        v3Sub_box.addWidget(self.chk2_saveData)
        v3Sub_box.addWidget(self.chk1)
        v3Sub_box.addWidget(self.lbl_verCheck)
        v3Sub_box.addWidget(self.lbl_errMsg)
        v3Sub_box.addWidget(self.lbl_lot)
        v3Sub_box.addStretch()

        h3_box = QHBoxLayout()
        h3_box.addWidget(self.btnRun)
        h3_box.addWidget(self.btnStop)
        h3_box.addWidget(self.btn_reset)
        h3_box.addWidget(self.btn_closeAll)
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

        self.setLayout(v_box)

        #signal
        self.btnStop.clicked.connect(self.btn_Stop_pressed)
        self.btnRun.clicked.connect(self.btn_Run_pressed)
        self.btn_reset.clicked.connect(self.btn_reset_pressed)
        self.btn_closeAll.clicked.connect(self.btn_closeAll_pressed)

    def chk_mqlVer(self):
        broker1.get_zmq_ver()
        broker2.get_zmq_ver()
        broker1.init_symbol(symbols1)
        broker2.init_symbol(symbols2)

        if broker1.zmq_mt4_ver == zmq_ver_cfg  and broker2.zmq_mt4_ver == zmq_ver_cfg:
            self.lbl_verCheck.setText('MQL Ver Pass')
            self.lbl_verCheck.setStyleSheet('color: green')
        else:
            self.lbl_verCheck.setText('MQL Ver Fail')
            self.lbl_verCheck.setStyleSheet('color: red')
            self.btnRun.setDisabled(True)

    def chk_initialization(self):

        if not cfgData.readStatus:

            self.lbl_errMsg.setText('Init Error')
            self.btnRun.setDisabled(True)

    def Widget_Init(self):
        self.btnRun.setEnabled(True)
        self.btnStop.setDisabled(True)

    def btn_closeAll_pressed(self):
        print 'Close All Order'
        broker2.order_close_new(symbols2)

    def btn_Run_pressed(self):
        print 'Run Arbitrage 1 Leg'
        self.btnRun.setDisabled(True)
        self.btnStop.setEnabled(True)
        self.timer.timeout.connect(self.run_1Leg_arb)
        self.timer.start(100)

    def btn_Stop_pressed(self):
        print 'Stop Signal'
        self.btnRun.setEnabled(True)
        self.btnStop.setDisabled(True)
        self.btn_onOff.setPixmap(QPixmap('img\\off.png'))
        self.timer.stop()

    def btn_reset_pressed(self):
        print 'Reset Table'
        self.tbl_viewResult.clearContents()
        self.lbl_lot.setText('')

    def run_1Leg_arb(self):
        broker1.get_price(symbols1)
        broker2.get_price(symbols2)
        broker1.get_order_status(symbols1)
        broker2.get_order_status(symbols2)
        self.cal_gapPosNeg()

        broker1.get_acct_info()
        broker2.get_acct_info()
        lots = broker2.get_lots()
        acct_balance = broker2.balance
        lot_text = 'Lot=' + str(lots)
        self.lbl_lot.setText(lot_text)

        self.update_Table(symbols1)

        saveData = False
        timeChanged = False

        if broker1.tms > self.previous_tms:
            timeChanged = True
            self.previous_tms = broker1.tms
            if self.chk2_saveData.isChecked():
                saveData = True

        for i in range(len(symbols1)):

            next_step = pip_step * (broker2.trade_count[i] + 1)
            noTradeTime = vt.chk_OffTrade(start_day, start_time, end_day, end_time)
            preCheck = False

            if broker1.tms == broker2.tms and broker1.bid[i] != 0 and broker2.bid[
                i] != 0 and broker1.connection and broker2.connection:
                preCheck = True

                if saveData:
                    db.save2db(database, broker1.tms, broker1.company, symbols1[i], broker1.digits[i], broker1.bid[i],
                               broker1.ask[i])
                    db.save2db(database, broker2.tms, broker2.company, symbols2[i], broker2.digits[i], broker2.bid[i],
                               broker2.ask[i])

            if preCheck and not noTradeTime and acct_balance <= max_profit:
                self.btn_onOff.setPixmap(QPixmap('img\\on.jpg'))

                if broker2.trade_count[i] == 0:

                    mt4_comments = ' '
                    if self.pos[i] > arbitrage_open:

                        broker2.send_order(BUY, symbols2[i], broker2.ask[i], lots, SLIP, stop_loss, mt4_comments)  # IC Market
                        print 'broker 2: Open order buy for', symbols2[i]

                        timestamp = str(datetime.now().replace(microsecond=0))
                        text_msg = timestamp + '\n' + symbols2[i] + ': Open position BUY' + '\n' + 'Pos =' + \
                            str(self.pos[i]) + '\n' + 'Gap =' + str(self.gap[i])
                        if self.chk3_telegram.isChecked():
                            bot.send_message(chat_id=chat_id, text=text_msg)

                        # ['timestamp', 'symbol', 'countTrade', 'bidAsk', 'tradeType', 'level', 'posNeg']
                        data = [broker2.tms, symbols2[i], broker2.trade_count[i], broker2.ask[i], 'BUY', 'level1',
                                self.pos[i]]
                        write_2_file(data)

                    elif self.neg[i] < -arbitrage_open:

                        broker2.send_order(SELL, symbols2[i], broker2.bid[i], lots, SLIP, stop_loss, mt4_comments)  # IC Market
                        print 'broker 2: Open order sell for', symbols2[i]

                        timestamp = str(datetime.now().replace(microsecond=0))
                        text_msg = timestamp + '\n' + symbols2[i] + ': Open position SELL'
                        if self.chk3_telegram.isChecked():
                            bot.send_message(chat_id=chat_id, text=text_msg)

                        # ['timestamp', 'symbol', 'countTrade', 'bidAsk', 'tradeType', 'level', 'posNeg']
                        data = [broker2.tms, symbols2[i], broker2.trade_count[i], broker2.ask[i], 'SELL', 'level1',
                                self.neg[i]]
                        write_2_file(data)

                # to close position if price converge again
                elif broker2.trade_count[i] > 0:

                    mt4_comments = ' '
                    # self.chk_hit_SL(symbols2[i],i)

                    if broker2.order_type[i] == BUY and self.pos[i] < arbitrage_close and self.chk_closeValid(broker2,
                                                                                                              symbols2[i]):
                        broker2.order_close_new([symbols2[i]])
                        print 'broker 2: Close order'

                        timestamp = str(datetime.now().replace(microsecond=0))
                        text_msg = timestamp + '\n' + symbols2[i] + ': Close position BUY'
                        if self.chk3_telegram.isChecked():
                            bot.send_message(chat_id=chat_id, text=text_msg)

                        data = [broker2.tms, symbols2[i], broker2.trade_count[i], broker2.bid[i], 'CLOSE']
                        write_2_file(data)

                    elif broker2.order_type[i] == SELL and self.neg[i] > -arbitrage_close and self.chk_closeValid(broker2,
                                                                                                                  symbols2[
                                                                                                                      i]):
                        broker2.order_close_new([symbols2[i]])
                        print 'broker 2: Close order'

                        timestamp = str(datetime.now().replace(microsecond=0))
                        text_msg = timestamp + '\n' + symbols2[i] + ': Close position SELL'
                        if self.chk3_telegram.isChecked():
                            bot.send_message(chat_id=chat_id, text=text_msg)

                        data = [broker2.tms, symbols2[i], broker2.trade_count[i], broker2.ask[i], 'CLOSE']
                        write_2_file(data)

                    # open layer if price gap further

                    elif broker2.order_type[i] == BUY and self.pos[i] > next_step:

                        broker2.send_order(BUY, symbols2[i], broker2.ask[i], lots, SLIP, stop_loss, mt4_comments)  # IC Market
                        print 'broker 2: Open order buy for next lvl ', symbols2[i]

                        timestamp = str(datetime.now().replace(microsecond=0))
                        text_msg = timestamp + '\n' + symbols2[i] + ': Open position BUY for next level' + '\n' + mt4_comments
                        if self.chk3_telegram.isChecked():
                            bot.send_message(chat_id=chat_id, text=text_msg)

                        # ['timestamp', 'symbol', 'countTrade', 'bidAsk', 'tradeType', 'level', 'posNeg']
                        data = [broker2.tms, symbols2[i], broker2.trade_count[i], broker2.ask[i], 'BUY', mt4_comments,
                                self.pos[i]]
                        write_2_file(data)

                    elif broker2.order_type[i] == SELL and self.neg[i] < - next_step:

                        broker2.send_order(SELL, symbols2[i], broker2.bid[i], lots, SLIP, stop_loss, mt4_comments)  # IC Market
                        print 'broker 2: Open order sell for next lvl ', symbols2[i]

                        timestamp = str(datetime.now().replace(microsecond=0))
                        text_msg = timestamp + '\n' + symbols2[i] + ': Open position SELL for next level' + '\n' + mt4_comments
                        if self.chk3_telegram.isChecked():
                            bot.send_message(chat_id=chat_id, text=text_msg)

                        # ['timestamp', 'symbol', 'countTrade', 'bidAsk', 'tradeType', 'level', 'posNeg']
                        data = [broker2.tms, symbols2[i], broker2.trade_count[i], broker2.bid[i], 'SELL', mt4_comments,
                                self.neg[i]]
                        write_2_file(data)

            else:
                self.btn_onOff.setPixmap(QPixmap('img\\off.png'))

                # to close position if price converge again
                if broker2.trade_count[i] > 0 and preCheck:

                    if broker2.order_type[i] == BUY and self.pos[i] < arbitrage_close and self.chk_closeValid(broker2,
                                                                                                              symbols2[i]):
                        broker2.order_close_new([symbols2[i]])
                        print 'broker 2: Close order'

                        timestamp = str(datetime.now().replace(microsecond=0))
                        text_msg = timestamp + '\n' + symbols2[i] + ': Close position BUY'
                        bot.send_message(chat_id=chat_id, text=text_msg)

                        data = [broker2.tms, symbols2[i], broker2.trade_count[i], broker2.bid[i], 'CLOSE']
                        write_2_file(data)

                    elif broker2.order_type[i] == SELL and self.neg[i] > -arbitrage_close and self.chk_closeValid(broker2,
                                                                                                                  symbols2[
                                                                                                                      i]):
                        broker2.order_close_new([symbols2[i]])
                        print 'broker 2: Close order'

                        timestamp = str(datetime.now().replace(microsecond=0))
                        text_msg = timestamp + '\n' + symbols2[i] + ': Close position SELL'
                        bot.send_message(chat_id=chat_id, text=text_msg)

                        data = [broker2.tms, symbols2[i], broker2.trade_count[i], broker2.ask[i], 'CLOSE']
                        write_2_file(data)

    def chk_closeValid(self, broker, symbol):
        closeValid = False

        openTime, mt4ServerTime = broker.get_openTime(symbol)
        allowedCloseTime = openTime + dt.timedelta(seconds= scalpingRuleTime)

        if mt4ServerTime > allowedCloseTime:
                closeValid=True

        return closeValid

    def cal_gapPosNeg(self):
        self.gap = []
        self.pos = []
        self.neg = []

        for i in range(len(pairs)):

            if broker1.digits[i] < broker2.digits[i]:
                digits = broker1.digits[i]
            else:
                digits = broker2.digits[i]

            self.gap.append(0.0)
            self.pos.append(0.0)
            self.neg.append(0.0)
            self.gap[i] = round((broker1.avg_price[i] - broker2.avg_price[i]) * math.pow(10, digits), 1) + gaps_offset[i]
            self.pos[i] = round((broker1.bid[i] - broker2.ask[i]) * math.pow(10, digits), 1) + gaps_offset[i]
            self.neg[i] = round((broker1.ask[i] - broker2.bid[i]) * math.pow(10, digits), 1) + gaps_offset[i]

    def update_Table(self, symbols):
        for i in range(len(symbols)):
            self.tbl_viewResult.setItem(i, 0, QTableWidgetItem(symbols[i][:6]))
            self.tbl_viewResult.setItem(i, 1, QTableWidgetItem(str(broker1.tms)))
            self.tbl_viewResult.setItem(i, 2, QTableWidgetItem(str(broker1.bid[i])))
            self.tbl_viewResult.setItem(i, 3, QTableWidgetItem(str(broker1.ask[i])))
            self.tbl_viewResult.setItem(i, 4, QTableWidgetItem(str(broker2.bid[i])))
            self.tbl_viewResult.setItem(i, 5, QTableWidgetItem(str(broker2.ask[i])))
            self.tbl_viewResult.setItem(i, 6, QTableWidgetItem(str(broker1.avg_price[i])))
            self.tbl_viewResult.setItem(i, 7, QTableWidgetItem(str(broker2.avg_price[i])))
            self.tbl_viewResult.setItem(i, 8, QTableWidgetItem(str(self.gap[i])))
            self.tbl_viewResult.setItem(i, 9, QTableWidgetItem(str(self.pos[i])))
            self.tbl_viewResult.setItem(i, 10, QTableWidgetItem(str(self.neg[i])))
            self.tbl_viewResult.setItem(i, 11, QTableWidgetItem(str(gaps_offset[i])))

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
                    print 'broker 2: Hit Stop Loss'

                    timestamp = str(datetime.now().replace(microsecond=0))
                    text_msg = timestamp + '\n' + symbols2[i] + ': Hit Stop Loss'
                    if self.chk3_telegram.isChecked():
                        bot.send_message(chat_id=chat_id, text=text_msg)

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
        print 'Send telegram message: debug mode'
        timestamp = str(datetime.now().replace(microsecond=0))
        text_msg = timestamp + '\n' + 'test message sent from EA'
        bot.send_message(chat_id=chat_id, text=text_msg)

    def btn_sendOrder_pressed(self):
        print 'Send Order'
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
            broker1.get_price(selSymbols1)

            for s in range(len(selSymbols1)):
                broker1.send_order(BUY, selSymbols1[s], broker1.ask[s], LOTS, SLIP, stop_loss, 'test')
                broker1.send_order(SELL, selSymbols1[s], broker1.bid[s], LOTS, SLIP, stop_loss, 'test')

        elif not self.chk_broker1.isChecked() and self.chk_broker2.isChecked():
            broker2.get_price(selSymbols2)

            for s in range(len(selSymbols2)):
                broker2.send_order(BUY, selSymbols2[s], broker2.ask[s], LOTS, SLIP, stop_loss, 'test')
                broker2.send_order(SELL, selSymbols2[s], broker2.bid[s], LOTS, SLIP, stop_loss,'test')

        elif self.chk_broker1.isChecked() and self.chk_broker2.isChecked():
            broker1.get_price(selSymbols1)
            broker2.get_price(selSymbols2)

            for s in range(len(selSymbols1)):
                broker1.send_order(BUY, selSymbols1[s], broker1.ask[s], LOTS, SLIP, stop_loss, 'test')
                broker1.send_order(SELL, selSymbols1[s], broker1.bid[s], LOTS, SLIP, stop_loss, 'test')
                broker2.send_order(BUY, selSymbols2[s], broker2.ask[s], LOTS, SLIP, stop_loss, 'test')
                broker2.send_order(SELL, selSymbols2[s], broker2.bid[s], LOTS, SLIP, stop_loss, 'test')

    def btn_closeSingle_pressed(self):
        print 'Close selected pair(s)'
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
        print 'Close All Order'
        broker1.order_close_new(symbols1)
        broker2.order_close_new(symbols2)

    def btn_getPrice_pressed(self):
        print 'Get Quotes'
        broker1.get_price(symbols1)
        broker2.get_price(symbols2)
        FormWidget.cal_gapPosNeg()

        FormWidget.update_Table(symbols1)

    def btn_reset_pressed(self):
        print 'Reset Screen'
        self.txt_symbol.clear()
        self.txt_promt.clear()
        self.chk_broker1.setChecked(False)
        self.chk_broker2.setChecked(False)
        self.chk_query.setChecked(False)

    def btn_excel_pressed(self,q):

        sql = str(self.txt_promt.toPlainText())
        print sql

        if q.isChecked():
            db.exportCustom(database, csv_filename, sql)
        else:
            db.export2excel(database, csv_filename)

        print 'export data to CSV successful !!!'


# Function to send commands to ZeroMQ MT4 EA
def remote_send(socket, data):

    msg = None
    try:

        socket.send(data)
        msg = socket.recv_string()

    except zmq.Again as e:
        print ("1.Waiting for PUSH from MetaTrader 4.. :", e)
        sleep(1)

# Function to retrieve data from ZeroMQ MT4 EA
def remote_pull(socket):

    msg = None
    try:
        msg = socket.recv()
    # msg = socket.recv(flags=zmq.NOBLOCK)

    except zmq.Again as e:
        print ("2.Waiting for PUSH from MetaTrader 4.. :", e)
        sleep(3)

    return msg

class broker_class:
    tms = None
    trade_count = None
    err_msg = None
    req_socket = None
    pull_socket = None
    symbol = None
    magic_number = None

    def __init__(self, broker, magic_no):
        # def __init__(self, broker, pair, magic_no):
        self.get_socket(broker)
        # self.symbol = pair
        self.magic_number = magic_no

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

    def get_price(self, symbols):

        sym = ''
        for s in symbols:
            sym = sym + '|' + s

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
    def get_order_status(self, symbols):
        sym = ''
        for s in symbols:
            sym = sym + '|' + s

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

        print req_count
        remote_send(self.req_socket, req_count)
        sys.exit()

        msg = remote_pull(self.pull_socket)

        print msg

        if msg is not None:
            quote = msg.split('|')
            for i in range(len(symbols)):
                # print i, '\t', quote[i + 1]
                self.profit[i] = int(float(quote[i+1]))

        print self.profit

    def send_order(self, order_type, symbol, price, lot=0.01, slip=10, stop_loss=0, comments="no comments"):

        #format 'TRADE|OPEN|ordertype|symbol|openprice|lot|SL|TP|Slip|comments|magicnumber'

        order = "TRADE|OPEN|"+ str(order_type)+"|" + symbol +"|"+ str(price)+"|"+ str(lot)+ "|" + str(stop_loss)+ "|0|" + str(slip)+"|"+comments +"|"+str(self.magic_number)
        print order

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

        print close_order
        # sys.exit()

        remote_send(self.req_socket, close_order)

    def get_zmq_ver(self):

        chk_ver = 'EAVERSION'
        print 'Check ZMQ version'
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

    def init_symbol(self, symbols):

        str_symb = ''
        for s in symbols:
            str_symb = str_symb + '|' + s

        init_symbols = 'INITIALIZE' + str_symb
        print 'Initialize MT4 Symbols ...'

        remote_send(self.req_socket, init_symbols)

    def get_lots(self):
        lots = 0.0

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
            lots = round((usdPerPip / lot2usd_ratio),rounders)
        elif RISK == 'manual':
            lots = LOTS

        return lots

def write_2_file(data_2_write):
    with open(filename, 'a') as f:
        writer = csv.writer(f)
        writer.writerow(data_2_write)
    f.close()

# Run Tests -----------------------------------------------------------
print 'PROGRAM START'

bot = telegram.Bot(token= token)

broker1 = broker_class(ip_1, magic_number)
broker2 = broker_class(ip_2, magic_number)

#Parameters
BUY = 0
SELL = 1

symbols1=[]
symbols2=[]

for pair in pairs:
    brok1_pair = pair + suffix_bro1
    brok2_pair = pair + suffix_bro2
    symbols1.append(brok1_pair)
    symbols2.append(brok2_pair)

print symbols1,'\n',symbols2

#------------------------ write to log file -------------
directory = 'data'
filename = directory + '\\' + 'arbitrage.log'
header=['timestamp','symbol','countTrade','bidAsk','tradeType','level','posNeg']

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
superIpin = TestWindow()
superIpin.show()
sys.exit(app.exec_())
