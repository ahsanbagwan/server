#-------------------------------------------------------------------------------
# Copyright (c) 2014 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------

from .gamesContainer import  gamesContainerClass

from games.supremeDestructionGame import supremeDestructionGame

class supremeDestructionGamesContainerClass(gamesContainerClass):
    '''Class for custom supremeDestruction games'''

    def __init__(self, db, parent = None):
        super(supremeDestructionGamesContainerClass, self).__init__("supremeDestruction", "Supreme Destruction", db, parent)

    def addBasicGame(self, player, newgame, gamePort):
        
        playerLogin = player.getLogin()
        playerUuid = player.getId()
        playerState = player.getAction()
        gameUuid = self.createUuid(playerUuid)
        
        if playerState == "PLAYING" :
            return False
        elif playerState == "HOST" :
            return False
        elif playerState == "JOIN" :
            return False

        ngame = supremeDestructionGame(gameUuid, self)
        ngame.setLobbyState('Idle')
        ngame.setGameHostName(playerLogin)
        ngame.setGameHostUuid(playerUuid)
        ngame.setGameHostPort(gamePort)
        ngame.setGameHostLocalPort(gamePort)
        ngame.setGameName(newgame)
        self.games.append(ngame)
        return ngame
