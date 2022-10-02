
import json


def get_instance():
  last_main_size = None
  
  with open('scrcpy.json', "r", encoding="utf8") as f:
      data = json.load(f)
  
  r0 = data['r0']
  r1 = data['r1']  
    

  def on_main_size_change(main_x, main_y, main_xpw, main_yph):
    nonlocal last_main_size
    
    if (not (last_main_size == None)):
        last_main_width = last_main_size[2] - last_main_size[0]
        last_main_height = last_main_size[3] - last_main_size[1] - 20

        now_main_width = main_xpw - main_x
        now_main_height = main_yph - main_y - 20

        v = abs(last_main_width / last_main_height -
                now_main_height / now_main_width)
        print(last_main_width, last_main_height ,now_main_width,now_main_height)
        print('rotate radio', v)

        if v < 0.5: 
          print(now_main_width / now_main_height)
          if (now_main_width / now_main_height - 1) > 0.3:
            print('main window size changed')

            last_main_size = (main_x, main_y, main_xpw, main_yph)
            return (True, (r0[0], r0[1], r0[2], r0[3]))
          elif  (now_main_width / now_main_height - 1) < -0.3:
            last_main_size = (main_x, main_y, main_xpw, main_yph)
            return (True, (r1[0], r1[1], r1[2], r1[3]))
          
          
    last_main_size = (main_x, main_y, main_xpw, main_yph)
    return (False ,(0,0,0,0))
        
  return {
    'on_main_size_change': on_main_size_change
  }
  