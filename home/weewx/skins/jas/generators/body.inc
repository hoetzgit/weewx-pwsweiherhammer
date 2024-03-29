##    Copyright (c) 2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

    <div class="container">
    #if $getVar('$Extras.pages.' + $page + '.zoomControl', False)
      #include "sections/zoomControl.inc"
    #end if

    #set charts = $getVar('Extras.chart_definitions')
    #set processing_grid = False
    #for $section in $getVar('Extras.pages.' + $page)
      #set include_name = $getVar('Extras.pages.' + $page + '.' + $section + '.filename', None)
      ## ToDo: cleanup to not use continue
      #if not isinstance($Extras.pages[$page][$section],dict)
        #continue
      #end if
      #set layout = $getVar('Extras.pages.' + $page + '.' + $section + '.layout', 'grid')
      #if $layout == 'grid' 
        #if not $processing_grid
          #set processing_grid = True
          <div class="row graphrow align-content-start">
        #end if
      #else
        #if processing_grid
          #set processing_grid = False
          </div>
          <div class="row">
        #end if
      #end if
      #if $section in $charts
        #set global section_global = $section
        #include 'sections/chart.inc'
        #set global section_global = None
      #else if $include_name is not None
        #include $include_name
      #else
        #include 'sections/' + $section + '.inc'
      #end if
      #if $layout != 'grid'
        </div>
      #end if
    #end for
    #if $processing_grid
      </div>
    #end if
    </div>     
    #set data = '<script src="../charts/' + $page_name_global + '.js"></script>'
    $data
    