import pytest

from server.players import PlayerState
from server.protocol import Protocol
from tests.utils import fast_forward

from .conftest import connect_and_sign_in, read_until_command

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def invite_to_party(proto: Protocol, recipient_id: int) -> None:
    await proto.send_message({
        'command': 'invite_to_party',
        'recipient_id': recipient_id,
    })


async def accept_party_invite(proto: Protocol, sender_id: int) -> None:
    await proto.send_message({
        'command': 'accept_party_invite',
        'sender_id': sender_id,
    })


@fast_forward(60)
async def test_invite_party_workflow(lobby_server, party_service):
    """ Simulates the lifecycle of a party.
        1. Player sends party invite
        2. Player accepts party invite
        3. Player sets factions
        4. Player readies up
        5. Player unreadies
        6. Player kicks other player from party
        7. Player leaves party
    """
    test_id, _, proto = await connect_and_sign_in(
        ('test', 'test_password'), lobby_server
    )

    rhiza_id, _, proto2 = await connect_and_sign_in(
        ('rhiza', 'puff_the_magic_dragon'), lobby_server
    )

    await read_until_command(proto, 'game_info')
    await read_until_command(proto2, 'game_info')

    # 1. Player sends party invite
    await invite_to_party(proto, rhiza_id)

    msg = await read_until_command(proto2, 'party_invite')
    assert msg == {'command': 'party_invite', 'sender': test_id}

    # 2. Player accepts party invite
    await accept_party_invite(proto2, test_id)

    msg1 = await read_until_command(proto, 'update_party')
    msg2 = await read_until_command(proto2, 'update_party')
    assert msg1 == msg2
    assert msg1 == {
        'command': 'update_party',
        'owner': test_id,
        'members': [
            {
                'factions': [True, True, True, True],
                'player': test_id,
                'ready': False
            },
            {
                'factions': [True, True, True, True],
                'player': rhiza_id,
                'ready': False
            }
        ]
    }
    # 3. Player sets factions
    await proto.send_message({
        'command': 'set_party_factions',
        'factions': [True, False, False, False]
    })
    msg1 = await read_until_command(proto, 'update_party')
    msg2 = await read_until_command(proto2, 'update_party')
    assert msg1 == msg2
    assert msg1 == {
        'command': 'update_party',
        'owner': test_id,
        'members': [
            {
                'factions': [True, False, False, False],
                'player': test_id,
                'ready': False
            },
            {
                'factions': [True, True, True, True],
                'player': rhiza_id,
                'ready': False
            }
        ]
    }

    # 4. Player readies up
    await proto2.send_message({'command': 'ready_party'})

    msg1 = await read_until_command(proto, 'update_party')
    msg2 = await read_until_command(proto2, 'update_party')
    assert msg1 == msg2
    assert msg1 == {
        'command': 'update_party',
        'owner': test_id,
        'members': [
            {
                'factions': [True, False, False, False],
                'player': test_id,
                'ready': False
            },
            {
                'factions': [True, True, True, True],
                'player': rhiza_id,
                'ready': True
            }
        ]
    }

    # 5. Player unreadies
    await proto2.send_message({'command': 'unready_party'})

    msg1 = await read_until_command(proto, 'update_party')
    msg2 = await read_until_command(proto2, 'update_party')
    assert msg1 == msg2
    assert msg1 == {
        'command': 'update_party',
        'owner': test_id,
        'members': [
            {
                'factions': [True, False, False, False],
                'player': test_id,
                'ready': False
            },
            {
                'factions': [True, True, True, True],
                'player': rhiza_id,
                'ready': False
            }
        ]
    }

    # 6. Player kicks other player from party
    await proto.send_message({
        'command': 'kick_player_from_party',
        'kicked_player_id': rhiza_id,
    })

    msg1 = await read_until_command(proto, 'update_party')
    msg2 = await read_until_command(proto2, 'update_party')
    assert msg1 == msg2
    assert msg1 == {
        'command': 'update_party',
        'owner': test_id,
        'members': [
            {
                'factions': [True, False, False, False],
                'player': test_id,
                'ready': False
            }
        ]
    }

    # 7. Player leaves party
    await proto.send_message({'command': 'leave_party'})

    msg = await read_until_command(proto, 'update_party')
    assert msg == {
        'command': 'update_party',
        'owner': test_id,
        'members': []
    }

    assert party_service.player_parties == {}


async def test_invite_non_existent_player(lobby_server):
    test_id, _, proto = await connect_and_sign_in(
        ('test', 'test_password'), lobby_server
    )

    await read_until_command(proto, 'game_info')

    await invite_to_party(proto, 2)

    msg = await proto.read_message()
    assert msg == {
        'command': 'notice',
        'style': 'error',
        'text': "The invited player doesn't exist"
    }


@fast_forward(60)
async def test_multiple_invites_same_player(lobby_server):
    test_id, _, proto = await connect_and_sign_in(
        ('test', 'test_password'), lobby_server
    )

    rhiza_id, _, proto2 = await connect_and_sign_in(
        ('rhiza', 'puff_the_magic_dragon'), lobby_server
    )

    newbie_id, _, proto3 = await connect_and_sign_in(
        ('newbie', 'password'), lobby_server
    )

    # Send first invite
    await invite_to_party(proto, newbie_id)

    msg = await read_until_command(proto3, 'party_invite')
    assert msg == {'command': 'party_invite', 'sender': test_id}

    # Accept first invite
    await accept_party_invite(proto3, test_id)

    await read_until_command(proto, 'update_party')
    await read_until_command(proto3, 'update_party')

    # Send second invite
    await invite_to_party(proto2, newbie_id)

    msg = await read_until_command(proto3, 'party_invite')
    assert msg == {'command': 'party_invite', 'sender': rhiza_id}


async def test_accept_invite_non_existent(lobby_server):
    test_id, _, proto = await connect_and_sign_in(
        ('test', 'test_password'), lobby_server
    )

    await read_until_command(proto, 'game_info')

    await accept_party_invite(proto, 2)

    msg = await proto.read_message()
    assert msg == {'command': 'notice', 'style': 'error', 'text': "The inviting player doesn't exist"}


async def test_kick_player_non_existent(lobby_server):
    test_id, _, proto = await connect_and_sign_in(
        ('test', 'test_password'), lobby_server
    )

    await read_until_command(proto, 'game_info')

    await proto.send_message({
        'command': 'kick_player_from_party',
        'kicked_player_id': 2,
    })

    msg = await proto.read_message()
    assert msg == {'command': 'notice', 'style': 'error', 'text': "The kicked player doesn't exist"}


async def test_party_while_queuing(lobby_server):
    test_id, _, proto = await connect_and_sign_in(
        ('test', 'test_password'), lobby_server
    )

    await read_until_command(proto, 'game_info')

    await proto.send_message({
        'command': 'game_matchmaking',
        'state': 'start',
        'faction': 'uef'
    })
    await read_until_command(proto, "search_info")

    await proto.send_message({'command': 'invite_to_party'})
    msg = await proto.read_message()
    assert msg == {'command': 'invalid_state', 'state': PlayerState.SEARCHING_LADDER.value}

    await proto.send_message({'command': 'accept_party_invite'})
    msg = await proto.read_message()
    assert msg == {'command': 'invalid_state', 'state': PlayerState.SEARCHING_LADDER.value}

    await proto.send_message({'command': 'kick_player_from_party'})
    msg = await proto.read_message()
    assert msg == {'command': 'invalid_state', 'state': PlayerState.SEARCHING_LADDER.value}


@fast_forward(60)
async def test_join_party_after_disband(lobby_server):
    p1_id, _, proto = await connect_and_sign_in(
        ('ladder1', 'ladder1'), lobby_server
    )

    p2_id, _, proto2 = await connect_and_sign_in(
        ('ladder2', 'ladder2'), lobby_server
    )

    await read_until_command(proto, 'game_info')
    await read_until_command(proto2, 'game_info')

    # Player 1 invites player 2
    await invite_to_party(proto, p2_id)

    await read_until_command(proto2, 'party_invite')

    await accept_party_invite(proto2, p1_id)

    await read_until_command(proto, 'update_party')
    await read_until_command(proto2, 'update_party')

    await proto2.send_message({'command': 'leave_party'})
    await read_until_command(proto, 'update_party')
    await proto.send_message({'command': 'leave_party'})

    # Now player 2 invites player 1
    await invite_to_party(proto2, p1_id)

    await read_until_command(proto, 'party_invite')

    await accept_party_invite(proto, p2_id)

    await read_until_command(proto, 'update_party')
    await read_until_command(proto2, 'update_party')
