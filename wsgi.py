# -*- coding: utf-8 -*-

import os
import datetime

# Create an application instance that web servers can use. We store it as
# "application" (the wsgi default) and also the much shorter and convenient
# "app".

def create_app():

  from run_banca import application
  return application

application = app = create_app()



@app.context_processor
def template_extras():

    return {'enumerate': enumerate, 'len': len, 'datetime': datetime}

if __name__ == '__main__':
    application.run()
    
    
