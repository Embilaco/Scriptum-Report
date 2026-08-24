#!/usr/bin/env python3
# coding: utf-8
#
# part of:
#   S C R I P T U M
#

from typing import Any, Optional

from ..tag.tag import Tag
from .base import Element
from .protocols import TableSource

# generic class that can work on tables 

class TableElement(Element):
    """TableElement class"""
    def __init__(self):
        """feed it with one element"""
        super().__init__()
        self.type = 'table'
        
    def __repr__(self) -> str:
        mystr = [f'element of type table: {self.id!r}']
        if hasattr(self.thing, 'is_placeholder') and self.thing.is_placeholder:
            mystr += [' so far, so empty - only a placeholder']
        else:
            try:
                mystr += [
                    f" cols={len(self.thing.table.rows[0].cells)} rows={len(self.thing.table.rows)}"
                ]
            except:
                mystr += [f'this is a {self.thing!r} {self.thing.shape_type}']
        return ':'.join(mystr)
        

    def resizeTable(self, ncols: int, nrows: int) -> None:
        """fix rows and columns compared to required ones if the element is a table
        yet we cannot remove rows and columns!
        """
        
        table = self.thing.table
        
        hasrows = len(table.rows)
        hascols = len(table.columns)
        
        if nrows > hasrows:
            for i in range(nrows-hasrows):
                table.add_row()
        if ncols > hascols:
            width = table.columns[-1].width
            for i in range(ncols-hascols):
                table.add_column(width)
        # can we delete as well? should we?
        # yet not possible, need to create a low level function

    def fillTable(self, tableValueObject: TableSource) -> None:
        """how to fill a table
        
        """

        table = self.thing.table
        if tableValueObject.exists: # file exists
            data = tableValueObject.content.data
            cols = tableValueObject.content.cols
            rows = tableValueObject.content.rows
            #print('work in existing table', cols, rows, data)
            self.resizeTable(cols,rows)
            for i,row in enumerate(table.rows):
                #print(i,row)
                for j,cell in enumerate(row.cells):
                    #print(j,cell)
                    try: # in case table is bigger than data
                        cell.text = str(data[i][j]) 
                    except Exception as e:
                        #print('EXCEPTION',e)
                        pass
        else:
            # add a message: the source explains itself when it does not exist
            table.rows[0].cells[0].text = str(tableValueObject)


    
