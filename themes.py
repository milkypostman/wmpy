default = {
        'normfg' : '#000000',
        'normbg' : '#c1c48b',
        'normborder' : '#81654f',
        'focusfg' : '#000000',
        'focusbg' : '#81654f',
        'focusborder' : '#000000',

        'volume_fglow' : '#cccccc',
        'volume_fgmed' : '#00cc00',
        'volume_fghigh' : '#cc0000',
        }

green = {
        'normfg' : '#FFFFFF',
        'normbg' : '#222222',
        'normborder' : '#333333',
        'focusfg' : '#FFFFaa',
        'focusbg' : '#007700',
        'focusborder' : '#88ff88',

        'mpd_fg' : '#FFFFaa',
        'weather_hotfg' : '#c51102',
        'weather_coldfg' : '#3a4ebe',
        }


klav = default.copy()

klav.update({
        'normfg' : '#afd700',
        'normbg' : '#000000',
        'normborder' : '#000000',
        'focusfg' : '#e2baf1',
        'focusbg' : '#000000',
        'focusborder' : '#000000',
        'mpd_fg' : '#009ed7',
        'clock_fg' : '#ffffff', 
        })
klav['focuswin'] = ' '.join( (klav['focusfg'], klav['focusbg'], '#e2baf1') )

subtle = default.copy()
subtle.update({
        'normfg' : '#ffffff',
        'normbg' : '#5d5d5d',
        'normborder' : '#5d5d5d',
        'focusfg' : '#ffffff',
        'focusbg' : '#ff00a8',
        'focusborder' : '#ff00a8',
        'mpd_fg' : '#009ed7',
        'clock_fg' : '#ff77da', 
        })
#subtle['normwin'] = ' '.join( (subtle['normfg'], subtle['normbg'], '#000000') )
