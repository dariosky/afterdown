from afterdown.core.utils import guessit_video_type, guessit_video_title

SERIE_EXAMPLES = (
    'Treme.1x03.Right.Place,.Wrong.Time.HDTV.XviD-NoTV.avi',
    'The.Night.of.Part.6.HDTV.x264-BATV[ettv].mkv',
)

FILM_EXAMPLES = (
    'unlearning.mp4',
)


def expecting_guess(filename_list, expected_type):
    for filename in filename_list:
        t = guessit_video_type(filename)
        print(filename, guessit_video_title(filename), t)
        assert t == expected_type


def test_guessit_serie():
    expecting_guess(SERIE_EXAMPLES, 'serie')


def test_guessit_film():
    expecting_guess(FILM_EXAMPLES, 'movie')
