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
        }


klav = default

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

