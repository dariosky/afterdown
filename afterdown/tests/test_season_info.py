import pytest

from afterdown.core.season_info import get_episode_infos


def test_name_examples():
    assert get_episode_infos('Card.S03e01.ITA.ENG.XviD.Subs.DLMux-BlackBIT') == ('03', '01')
    assert get_episode_infos('1e12 - The episode name.mp4') == ('01', '12')
    assert get_episode_infos('person.of.interest.414.hdtv-lol') == ('04', '14')
    assert get_episode_infos('stalker.107.hdtv-lol.mp4') == ('01', '07')
    assert get_episode_infos('GameofThrones S6 Ep2 720p x265 Dolby 2.0   KTM3.mp4') == ('06', '02')
    assert get_episode_infos('2.Broke.Girls.4x22.E.ux.x264-GiuseppeTnT.mkv') == ('04', '22')


def test_no_season():
    assert get_episode_infos('01 - The episode name.mp4') == (None, '01')
    assert get_episode_infos('Episode 10 - War Stories.mkv') == (None, '10')
    assert get_episode_infos('Ep10 - War Stories.mkv') == (None, '10')
    assert get_episode_infos('E.10 - War Stories.mkv') == (None, '10')


def test_x_format():
    assert get_episode_infos('La que se avicina 1x02 bla bla bla') == ('01', '02')


if __name__ == '__main__':
    pytest.main()
