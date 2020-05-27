#!/usr/bin/python
# -*- coding: utf-8 -*-
import constants
import pyodbc
import numpy as np
from datetime import datetime
import re
from decimal import Decimal
import math
import datetime
import numpy as np

class FdmFileGen:
    conn = pyodbc.connect('Driver={SQL Server};'
                      'Server=IE1FLTHNYBPQ2;'
                      'Database=skyconnect;'
                      'Trusted_Connection=yes;')

    # Rocket simulates a rocket ship for a game,
    #  or a physics simulation.

    def Reverse(self, s):
        return s[::-1]
    
    def FindLowestUnusedConfigNum(self):
        lowestAvailableConfigNum = -1
        cursor = conn.cursor()
        query = 'SELECT DISTINCT configNum FROM [sqlFdm].[dbo].[fdmConfigs] ORDER BY configNum'
        cursor.execute(query)
        Array = []
        for row in cursor: 
            Array += [row[0]]
        rowCount = len(Array)        
        cursor.execute(query)  
        if (rowCount > 0):
            lowestAvailableConfigNum = 	Array[rowCount - 1] + 1	
            for x in range(1, rowCount):
                possibleConfigNum = int(Array[x - 1]) + 1
                if (Array[x] > possibleConfigNum):
                    lowestAvailableConfigNum = possibleConfigNum
                    break
        else:
            lowestAvailableConfigNum = 1
        
        return lowestAvailableConfigNum

    def LookupFdmEventDesignator(self, label):
        fdmEventDesignator = 0;
        nLabel = int(label)
        labelToUse = label
        if (labelToUse == 0):
            fdmEventDesignator = int("0x38", 16)
        elif(labelToUse <= 377):
            fdmEventDesignator = int("0x3C", 16)
        else:
            fdmEventDesignator = label - 400
        return fdmEventDesignator

    def GetByteSubarrayInReverse(self, sourceArray, startPosition, length):
        resultArray = []
        for x in range(0,length):
            resultArray += sourceArray[startPosition + length - 1 - x]
        return resultArray

    def fnConvertDateTime(self, datePart, timePart):
        hour = 0
        minute = 0
        second = 0
        year = 0
        month = 0
        day = 0
        try:
            dotPos = timePart.index(".")
            if(((dotPos > 0) & (dotPos < 6)) | ((dotPos == -1) & len(timePart) == 5)):
                timePart = "0" + timePart
        except:
            print("no period in the string")
        timeMatch = re.search('([0-9]{2})([0-9]{2})([0-9]{2})', timePart)
        hour = int(timeMatch.group(1))
        minute = int(timeMatch.group(2))
        second = int(timeMatch.group(3))
        dateMatch = re.search('([0-9]{2})([0-9]{2})([0-9]{2})', datePart)
        day = int(dateMatch.group(1))
        month = int(dateMatch.group(2))
        year = 2000 + int(dateMatch.group(3))
        positionDateTime = datetime(year, month, day, hour, minute, second)
        return positionDateTime

    def fnConvertLatLong(self, latLong, hemi):
        formattedLatLong = Decimal(latLong)	
        dotPos = latLong.index(".")
        aLatLong = latLong
        dLatLong = Decimal(latLong[0:dotPos-2])	
        minutePartOfLatLong = Decimal(latLong[dotPos-2:])
        dLatLong += minutePartOfLatLong / 60
        if ((hemi == "S") | (hemi == "W")):
            dLatLong = -dLatLong
        return dLatLong
		
    def ConvertBinToAsciiHexV2(self, binaryIn, startingPosition, length):
        result = ""
        if (len(binaryIn) < (startingPosition + length)):
            return result
        asciiHex = [ "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F" ]
        for x in range(0,length):
            result += asciiHex[(int(binaryIn[x + startingPosition]) & 0xF0) >> 4]
            result += asciiHex[int(binaryIn[x + startingPosition]) & 0x0F]
        return result

    def ByteArrayToAsciiHexString(bytes, startPosition, length):
        hexString = ""
        for x in range(startPosition, startPosition + length):
            decimal_representation = int(bytes[x], 2)
            hexString += hex(decimal_representation)
        return hexString

    def IsDataTypeConsistent(dataType, recordSize):
        isConsistent = 1 if recordSize < 3000 else 0
        if(dataType == 0):
            isConsistent = 1 if recordSize == 8 else 0
        elif(dataType == 1):
            isConsistent = 1 if recordSize < 1000 else 0
        elif(dataType == 2|3|9|10|11|17|18|19|20|21|22|23|24|25|26|27|28|29|30):
            isConsistent = 1 if recordSize < 3000 else 0
        elif(dataType == 14|15|16):
            isConsistent = 1 if recordSize == 24 else 0
        elif(dataType == 12):
            isConsistent = 1 if recordSize == 12 else 0
        elif(dataType == 7|8):
            isConsistent = 1 if recordSize == 10 else 0
        elif(dataType == 6):
            isConsistent = 1 if recordSize == 13 else 0
        elif(dataType == 5):
            isConsistent = 1 if recordSize == 20 else 0
        elif(dataType == 4):
            isConsistent = 1 if ((recordSize - 8) % 5 == 0) else 0
        elif(dataType == 13):
            isConsistent = 1 if ((recordSize - 8) % 2 == 0) else 0
        return isConsistent
		
    def fnPostUnsentEmail(self, toEmail, toFriendlyName, fromEmail ,subject, msgBody, attachment, attachmentSize, attachmentFileName,isEncryptionRequested):
        cursor = conn.cursor()
        if(cursor.execute("INSERT INTO [sqlTrackerAgent].[dbo].[unsentEmail] ( attachment, attachmentFileName, attachmentSize, timePosted, toEmailAddress, toFriendlyName, subject, msgBody, encryptionRequested) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?  )", toEmail, toFriendlyName, fromEmail ,subject, msgBody, attachment, attachmentSize, attachmentFileName,isEncryptionRequested)):
            conn.commit()
            return 1
        return 0

    def PartialOrTemporaryOkHelper(self, configNum, version, sourceConfigNum, sourceVersion, fullCrc):
        msgText = ""
        query = ""
        data = ""
        data1 = ""
        cursor = conn.cursor()
        if ((sourceConfigNum == "New") | (sourceVersion == "New")):
            msgText = "Selected config is newly created, so Partial or Temporary is unavailable"
            return msgText
        if (fullCrc == ""):
            msgText = "Selected config has no computed CRC and may be flawed, so Partial or Temporary is unavailable"
            return msgText
        if ((sourceConfigNum != "") & (sourceVersion != "")):
            query += "WITH specifiedFcl AS (SELECT labelNumber FROM [sqlFdm].[dbo].[fdmConfigLabels] WHERE configNum ='" + configNum +"'"
            query += "AND [version] ='" + version + "')"
            query += "SELECT Count(fdmConfigLabels.ID)AS countOfDeletes FROM [sqlFdm].[dbo].[fdmConfigLabels] WHERE configNum = '"+ sourceConfigNum + "'"
            query += "AND [version] ='" + sourceVersion + "' AND labelNumber NOT IN(SELECT labelNumber FROM specifiedFcl)"
            for row in cursor.execute(query):
                data = row[0]
            if (int(data) > 0):
                msgText = "Selected config reflects " + str(data) + " label deletion"
                if (int(data) > 1):
                    msgText += "s"
                msgText += " from the previous configuration, so Partial and Temporary extent is not possible. "
                return msgText
            query1 = "WITH sourceFcl AS (SELECT labelNumber FROM [sqlFdm].[dbo].[fdmConfigLabels] WHERE configNum ='" + sourceConfigNum +"'"
            query1 += "AND [version] ='" + sourceVersion + "')"
            query1 += "SELECT Count(fdmConfigLabels.ID)AS countOfAdds FROM [sqlFdm].[dbo].[fdmConfigLabels] WHERE configNum = '"+ configNum + "'"
            query1 += "AND [version] ='" + version + "' AND labelNumber NOT IN(SELECT labelNumber FROM sourceFcl)"
            for row in cursor.execute(query1):
                data1 = row[0]
            if (int(data1) > 0):
                msgText = "Selected config reflects " + str(data1) + " label addition"
                if (int(data1) > 1):
                    msgText += "s"
                msgText += " from the previous configuration, so Partial and Temporary extent is not possible. "
                return msgText                
        return msgText
    def GetGsmSimSerialNumber(self, imeiNumber):
        gsmSimSerialNumber = ""
        cursor = conn.cursor()
        query = "SELECT deployedAssets.thirdSimSerialNumber FROM [sqlFdm].[dbo].[deviceConfigs] INNER JOIN sqlAssetManager.dbo.deployedAssets ON deviceConfigs.imeiNumber=deployedAssets.imeiNumber"
        query += " INNER JOIN sqlAssetManager.dbo.QBItems ON deployedAssets.itemCode=QBItems.itemCode "
        query += " INNER JOIN sqlAssetManager.dbo.SIMs ON deployedAssets.thirdSimSerialNumber=SIMs.simSerialNumber WHERE deviceConfigs.imeiNumber='"		
        query += imeiNumber + "' AND QBItems.isGsmDevice= 1 AND SIMs.voiceActivationState='ACTIVATED'"
        for row in cursor.execute(query):
            if(row[0] != ''):
                gsmSimSerialNumber = str(row[0])            
        return gsmSimSerialNumber

    def fn_buildMsgField(self, fromInt, toMsgString, toByte, toBit, toFldLen):
        fromBit = 0
        for i in range(0,toFldLen):
            fromBitVal = (fromInt >> fromBit) & 1
            if (fromBitVal == 1):
                toMsgString[toByte] |= ('\x01' << toBit)
            toBit += 1
            fromBit +=1
            if (toBit > 7):
                toBit = 0
                toByte -=1
        return

    def fn_buildMsgFieldInReverse(self, fromInt, toMsgString, toByte, toBit, toFldLen):
        fromBit = 0
        toByte = toByte - math.trunc((toBit + toFldLen) / 8)
        toBit = 8 - (toBit + toFldLen) % 8
        for i in range(0,toFldLen):
            fromBitVal = (fromInt >> fromBit) & 1
            if (fromBitVal == 1):
                toMsgString[toByte] |= ('\x01' << toBit)
            toBit += 1
            fromBit +=1
            if (toBit > 7):
                toBit = 0
                toByte -=1
        return

    def fnLogError(errorDescription):
        cursor = conn.cursor()
        current_time = datetime.datetime.now()
        cursor.execute("INSERT INTO [sqlAssetManager].[dbo].[errorLog] (errorDescription, errorTime) VALUES (?, ?)", errorDescription, current_time)
        conn.commit()
		
    def IsSourceTimeValid(self, fileBytes, startByte, powerUpTime):
        isValid = 0
        gpsYear = 2000 + int(fileBytes[startByte + 10])
        gpsMonth = int(fileBytes[startByte + 9])
        gpsDay = int(fileBytes[startByte + 8])
        byteGpsUptimeMs = []
        for i in range(startByte, startByte +4):
            byteGpsUptimeMs[i - startByte] = fileBytes[i]
        intGpsUptimeMs = prepare_bytes_on_string(byteGpsUptimeMs)
        byteGpsTime = []
        for i in range(startByte + 4, startByte + 8):
            byteGpsTime[i - startByte - 4] = fileBytes[i]
        intGpsTime = prepare_bytes_on_string(byteGpsTime)
        if ((gpsYear >= 2017) & (gpsYear < 2050) & (gpsMonth > 0) & (gpsMonth < 13) & (gpsDay > 0) & (gpsDay < 32)):
            gpsTime = datetime.date(gpsYear, gpsMonth, gpsDay)
            gpsTime = addSecs(gpsTime, intGpsTime)
            isValid = 1
        powerUpTime =  gpsTime + datetime.timedelta(milliseconds=intGpsTime)
        return isValid		

    def prepare_bytes_on_string():
        output = ''
        for i in range(0, len(array), 1):
        #Just as a reminder:
        #hex(x)                    #value: '0xffffbfde1605'
        #hex(x)[2:]                #value: 'ffffbfde1605'
        #hex(x)[2:].decode('hex')  #value: '\xff\xff\xbf\xde\x16\x05'
            output += hex(array[i])[2:].decode('hex')
        return output
		
    def addSecs(tm, secs):
        fulldate = datetime.datetime(100, 1, 1, tm.hour, tm.minute, tm.second)
        fulldate = fulldate + datetime.timedelta(seconds=secs)
        return fulldate.time()

    def DetermineExceedanceCode(self, summedValue, threshOpsIndexNum, minThresh, maxThresh, offset):
        exceedance = ""
        dSummedValue = 0
        dMinThresh = 0
        dMaxThresh = 0
        dOffset = 0
        if(float(summedValue)):
            dSummedValue = float(summedValue)
        else:
            return exceedance
        isMinThreshNumeric = 0
        isMaxThreshNumeric = 0
        if(float(minThresh)):
            isMinThreshNumeric = 1
            dMinThresh = float(minThresh)
        if(float(maxThresh)):
            isMaxThreshNumeric = 1
            dMaxThresh = float(maxThresh)
        if(float(maxThresh)):
            isOffsetNumeric = 1
            dOffset = float(offset)
        if (isOffsetNumeric):
            dSummedValue = dSummedValue + dOffset
        THRESHOPS_INSIDE_IGNORE = 0
        THRESHOPS_OUTSIDE_IGNORE = 1
        THRESHOPS_EQUALS_IGNORE = 2
        THRESHOPS_BITMASK_IGNORE = 3
        THRESHOPS_BITMASK_XOR_IGNORE = 4
        THRESHOPS_ABOVE_IGNORE = 5
        THRESHOPS_BELOW_IGNORE = 6
        THRESHOPS_INSIDE_ALERT = 16
        THRESHOPS_OUTSIDE_ALERT = 17
        THRESHOPS_EQUALS_ALERT = 18
        THRESHOPS_BITMASK_ALERT = 19
        THRESHOPS_BITMASK_XOR_ALERT = 20
        THRESHOPS_ABOVE_ALERT = 21
        THRESHOPS_BELOW_ALERT = 22
        if ((threshOpsIndexNum == THRESHOPS_INSIDE_IGNORE) | (threshOpsIndexNum == THRESHOPS_INSIDE_ALERT)):
            if (isMinThreshNumeric & isMaxThreshNumeric):
                if ((dSummedValue > dMinThresh) & (dSummedValue < dMaxThresh)):
                    exceedance = "I"
            elif (isMinThreshNumeric & (isMaxThreshNumeric != 1)):
                if (dSummedValue > dMinThresh):
                        exceedance = "I"
            elif (isMaxThreshNumeric & (isMinThreshNumeric != 1)):
                if (dSummedValue < dMaxThresh):
                    exceedance = "I"
        elif ((threshOpsIndexNum == THRESHOPS_OUTSIDE_IGNORE) | (threshOpsIndexNum == THRESHOPS_OUTSIDE_ALERT)):
            if (isMinThreshNumeric & isMaxThreshNumeric):
                if (dSummedValue < dMinThresh):
                    exceedance = "OB"
                elif (dSummedValue > dMaxThresh):
                    exceedance = "OA"
            elif (isMinThreshNumeric & (isMaxThreshNumeric != 1)):
                if (dSummedValue < dMinThresh):
                        exceedance = "OB"
            elif (isMaxThreshNumeric & (isMinThreshNumeric != 1)):
                if (dSummedValue > dMaxThresh):
                    exceedance = "OA"
        elif ((threshOpsIndexNum == THRESHOPS_EQUALS_IGNORE) | (threshOpsIndexNum == THRESHOPS_EQUALS_ALERT)):
            if (isMinThreshNumeric):
                if (dSummedValue == dMinThresh):
                        exceedance = "E"
            if (isMaxThreshNumeric):
                if (dSummedValue == dMaxThresh):
                    exceedance = "E"
        elif ((threshOpsIndexNum == THRESHOPS_ABOVE_IGNORE) | (threshOpsIndexNum == THRESHOPS_ABOVE_ALERT)):
            if (isMinThreshNumeric):
                if (dSummedValue > dMinThresh):
                    exceedance = "A"
            if (isMaxThreshNumeric):
                if (dSummedValue > dMaxThresh):
                        exceedance = "AA"
        elif ((threshOpsIndexNum == THRESHOPS_BELOW_IGNORE) | (threshOpsIndexNum == THRESHOPS_BELOW_ALERT)):
            if (isMaxThreshNumeric):
                if (dSummedValue < dMaxThresh):
                    exceedance = "B"
            if (isMinThreshNumeric):
                if (dSummedValue < dMinThresh):
                    exceedance = "BB"
        return exceedance
		
		
    def IsFdmRecordValid(self, fileBytes, firstByteOfDataRecord, lastGoodUptime, uptime, recordSize, dataType, isPrimaryRecordValid):
        isPrimaryRecordValid = 0
        if (len(fileBytes) < (firstByteOfDataRecord + recordSize)):
            return 0
        if(IsDataTypeConsistent(dataType, recordSize) == 0):
            return 0
        isPrimaryRecordValid = 1
        if (len(fileBytes) > (firstByteOfDataRecord + recordSize)):
            if (firstByteOfDataRecord + recordSize == len(fileBytes) - 2):
                if ((fileBytes[firstByteOfDataRecord + recordSize] == 0xFF) & (fileBytes[firstByteOfDataRecord + recordSize + 1] == 0xFF)):
                    return isPrimaryRecordValid
            if (len(fileBytes) < (firstByteOfDataRecord + recordSize + 8)):
                return 0
            byteRecordSize = []
            for i in range(firstByteOfDataRecord + recordSize, firstByteOfDataRecord + recordSize + 2):
                byteRecordSize[i - firstByteOfDataRecord - recordSize] = fileBytes[i]
            nextRecordSize = numpy.array(unpack('%sh' % len(byteRecordSize) / struct.calcsize('h'), byteRecordSize))
            nextDataType = fileBytes[firstByteOfDataRecord + recordSize + 2]
            byteMsSincePowerUp = []
            for i in range(firstByteOfDataRecord + 4, firstByteOfDataRecord + 8):
                byteMsSincePowerUp[i - firstByteOfDataRecord - 4] = fileBytes[i]
            int.from_bytes(byteMsSincePowerUp, byteorder='big', signed=False)
            nextUptime = float(dblMsSincePowerUp) / 1000
            if (((nextUptime - uptime) > 30) | (nextUptime < uptime)):
                return 0
            if (IsDataTypeConsistent(nextDataType, nextRecordSize) == 0):
                return 0
        return 1
		
    def fn_parseMsgField(self, fromMsgString, fromByte, fromBit, fromFldLen, fromFldType):
        TYPE_INT = 1
        fromBitVal = 0
        toInt = 0
        toBit = 0
        workByte = []
        for i in range(0, fromFldLen):
            workByte = fromMsgString[fromByte]
            fromBitVal = (int(workByte) >> fromBit) & 0x01
            if (fromBitVal == 1):
                toInt |= (1 << toBit)
            toBit = toBit + 1
            fromBit = fromBit + 1
            if (fromBit > 7):
                fromBit = 0
                fromByte = fromByte - 1
        if ((fromFldType == TYPE_INT) & (fromBitVal == 1)):
            fillLen = 32 - fromFldLen
            for i in range(0, fillLen):
                toInt |= (1 << toBit)
                toBit = toBit + 1
        return int(toInt)
		
		
    def FillFdmDataTypesTable(self):
        cursor = conn.cursor()
        query = "SELECT dataType, dataTypeName FROM [sqlFdm].[dbo].[ufdmDataTypeLookup]"
        row = []
        try:
            row = cursor.execute(query)
        except:
            fnLogError("FdmFileGenLib failed to FillFdmDataTypesTable; error: ")
        return row

    def ProcessMultiFloatDataTypes(self, recordSize, firstByteOfDataRecord, fileBytes, dataType, csDataType, fdmLabels, fileParseExceedanceEventsTable, dataRecordNumber, uptime,gpsTime, outputTextList, exceptionTextList, numberOfFloats):
        labelNumber = ""
        labelName = ""
        discretes = ""
        units = ""
        rawData = ""
        subType = ""
        threshOpsIndexNum = -1
        exceedance = ""
        minThresh = ""
        maxThresh = ""
        offset = ""
        alertPriority = ""
        if (recordSize != 8 + (4 * numberOfFloats)):
            return
        subTypeArray = ["firstValue", "secondValue", "thirdValue"]
        labelArray = [23, 24, 25, 26, 27]
        cursor = conn.cursor()
        query = "SELECT * FROM [sqlFdm].[dbo].[fdmLabels] WHERE uFdmDataType = '" + str(dataType) + "'"
        cursor.execute(query)
        Array = []
        for row in cursor: 
            Array += [row[0]]
        if (len(Array) == 0):
            return
        isAnySubTypePresent = 0
        for i in range(0, numberOfFloats):
            subType = subTypeArray[i]
            query1 = "SELECT * FROM [sqlFdm].[dbo].[fdmLabels] WHERE uFdmDataType = '" + str(dataType) + "' AND uFdmSubType='" + str(subType) + "'"
            cursor.execute(query1)
            Array1 = []
            for row in cursor: 
                Array1 += [row[0]]
            if(len(Array1) > 0):
                isAnySubTypePresent = 1
                break
        if(isAnySubTypePresent == 0):
            query = "SELECT * FROM [sqlFdm].[dbo].[fdmLabels] WHERE uFdmDataType = '" + str(dataType) + "'"
            cursor.execute(query)
            Array = []
            for row in cursor: 
                Array += [row[0]]
            if (len(Array) > 1 & (dataType not in labelArray)):
                return
            decodedData = "Float values: "
            for i in range(0, numberOfFloats):
                byteValue = []
                for j in range((firstByteOfDataRecord + 8 + (4 * i)), len(fileBytes),4):
                    byteValue[j - (firstByteOfDataRecord + 8 + (4 * i))] = fileBytes[j]
                floatOutput = struct.unpack('f', byteValue)
                decodedData = decodedData + str(floatOutput) + ","
                rawData = rawData + ByteArrayToAsciiHexString(byteValue, 0, 4) + ","
            cursor.execute(query)
            for row in cursor:
                labelNumber = getattr(row, 'labelNumber')
                labelNumber = str(labelNumber)
                labelName = getattr(row, 'labelName')
                labelName = str(labelName)
                units = getattr(row, 'units')
                units = str(units)
                threshOpsIndexNum = getattr(row, 'threshOpsIndexNum')
                threshOpsIndexNum = int(threshOpsIndexNum)
                minThresh = getattr(row, 'minThresh')
                minThresh = str(minThresh)
                maxThresh = getattr(row, 'maxThresh')
                maxThresh = str(maxThresh)
                offset = getattr(row, 'offset')
                offset = str(offset)
                alertPriority = getattr(row, 'alertPriority')
                alertPriority = str(alertPriority)
                AppendParseOutputRow(outputTextList, firstByteOfDataRecord, dataRecordNumber, dataType, uptime, gpsTime, labelNumber, labelName, discretes, decodedData, units, rawData, exceedance, fileParseExceedanceEventsTable, alertPriority)
                return
        for i in range(0, numberOfFloats):
            byteValue = []
            for j in range((firstByteOfDataRecord + 8 + (4 * i)), len(fileBytes),4):
                byteValue[j - (firstByteOfDataRecord + 8 + (4 * i))] = fileBytes[j]
            floatOutput = struct.unpack('f', byteValue)
            rawData = ByteArrayToAsciiHexString(byteValue, 0, 4)
            subType = subTypeArray[i]
            query = "SELECT * FROM [sqlFdm].[dbo].[fdmLabels] WHERE uFdmDataType = '" + str(dataType) + "' AND uFdmSubType='" + str(subType) + "'"
            cursor.execute(query)
            Array1 = []
            for row in cursor: 
                Array1 += [row[0]]
            if(len(Array1) == 0):
                continue
            elif(len(Array1) == 0):
                continue
            else:
                cursor.execute(query)
                for row in cursor:
                    labelNumber = getattr(row, 'labelNumber')
                    labelNumber = str(labelNumber)
                    labelName = getattr(row, 'labelName')
                    labelName = str(labelName)
                    units = getattr(row, 'units')
                    units = str(units)
                    threshOpsIndexNum = getattr(row, 'threshOpsIndexNum')
                    threshOpsIndexNum = int(threshOpsIndexNum)
                    minThresh = getattr(row, 'minThresh')
                    minThresh = str(minThresh)
                    maxThresh = getattr(row, 'maxThresh')
                    maxThresh = str(maxThresh)
                    offset = getattr(row, 'offset')
                    offset = str(offset)
                    alertPriority = getattr(row, 'alertPriority')
                    alertPriority = str(alertPriority)
            exceedance = DetermineExceedanceCode(str(floatOutput), threshOpsIndexNum, minThresh, maxThresh, offset)
            floatOutput = float + float(Offset)
            AppendParseOutputRow(outputTextList, firstByteOfDataRecord, dataRecordNumber, dataType, uptime, gpsTime, labelNumber, labelName, discretes, float(floatOutput), units, rawData, exceedance, fileParseExceedanceEventsTable, alertPriority)
    
    def AppendParseOutputRow(outputTextList, firstByteOfDataRecord, dataRecordNumber, dataType, uptime, gpsTime, labelNumber, labelName, discretes, decodedData, units, rawData, exceedance, fileParseExceedanceEventsTable, alertPriority):
        return
		
		
		
		
# Create a Rocket object, and have it start to move up.
conn = pyodbc.connect('Driver={SQL Server};'
                      'Server=IE1FLTHNYBPQ2;'
                      'Database=skyconnect;'
                      'Trusted_Connection=yes;')
my_result = FdmFileGen()
inputArray = ['1100','0','1','1','1','0','1','0','0','0','0','1','0','1','1']
resultString = my_result.ProcessMultiFloatDataTypes(20,0,inputArray,22,4,5,'',1,2222,3456,'','',3)
print (resultString)


