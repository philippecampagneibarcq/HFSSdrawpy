# -*- coding: utf-8 -*-
"""
Created on Mon Oct 28 16:18:36 2019

@author: Zaki
"""

import numpy as np

from ..utils import parse_entry, Vector
from ..parameters import layer_TRACK, \
                         layer_GAP, \
                         layer_RLC, \
                         layer_MESH, \
                         layer_MASK, \
                         layer_Default, \
                         eps

def create_port(self, widths=None, subnames=None, layers=None, offsets=0, name='port_0'):
    """
    Creates a port and draws a small triangle for each element of the port.
    This function does exactly the same thing as the Body method 'port' except
    that if 2 widths are provided and subnames, layers, and offsets are not,
    assumes a CPW port with first track then gap.

    Parameters
    ----------
    widths : float, 'VariableString' or list, optional
        Width of the different elements of the port. If None, assumes the
        creation of a constraint_port. The default is None.
    subnames : str or list, optional
        The cable's parts will be name cablename_subname. If None simply
        numbering the cable parts. The default is None.
    layers : int or list, optional
        Each layer is described by an int that is a python constant that one
        should import. If None, layer is the layer_Default The default is
        None.
    offsets : float, 'VariableString' or list, optional
        Describes the offset of the cable part wrt the center of the cable.
        The default is 0.
    name : str, optional
        Name of the port.

    Returns
    -------
    'Port'
        Returns a Port object

    """

    if widths is not None and isinstance(widths, list) and len(widths)==2:
        if subnames is None and layers is None :
            subnames = ['track', 'gap']
            layers = [layer_TRACK, layer_GAP]
            offsets = [0, 0]
    port, = self.port(widths=widths, subnames=subnames, layers=layers,
                     offsets=offsets, name=name)
    return [port]

def draw_connector(self, track, gap, bond_length, pcb_track, pcb_gap,
                   slope=1, tr_line=True, name='connector_0'):
    '''
    Draws a CPW connector for inputs and outputs.

    Inputs:
    -------
    name : (str) should be different from other connector's name
    iBondLength: (float) corresponds to dimension a in the drawing
    iSlope (float): 1 is 45 degrees to adpat lengths between Bonding pad and iout
    iLineTest (Bool): unclear, keep False

        ground plane
        +------+
        |       \
        |        \
        |   +-a-+\|
    iIn |   |.....| iOut
        |   +---+/|
        |        /
        |       /
        +------+

    Outputs:
    --------
    returns created entities with formalism [Port], [Entiy]
    '''

    track, gap, pcb_gap, pcb_track = parse_entry(track, gap, pcb_gap, pcb_track)
    bond_length, slope = parse_entry(bond_length, slope)

    adaptDist = (pcb_track/2-track/2)/slope

    points = [(pcb_gap-self.overdev, pcb_track/2+self.overdev),
              (pcb_gap+bond_length, pcb_track/2+self.overdev),
              (pcb_gap+bond_length+adaptDist, self.overdev+track/2),
              (pcb_gap+bond_length+adaptDist, -track/2-self.overdev),
              (pcb_gap+bond_length, -pcb_track/2-self.overdev),
              (pcb_gap-self.overdev, -pcb_track/2-self.overdev)]

    track_entity = self.polyline(points, layer=layer_TRACK,
                                 name=name+'_track')

    points = [(pcb_gap/2+self.overdev, pcb_gap+pcb_track/2-self.overdev),
             (pcb_gap+bond_length, pcb_gap+pcb_track/2-self.overdev),
             (pcb_gap+bond_length+adaptDist, gap+track/2-self.overdev),
             (pcb_gap+bond_length+adaptDist, -gap-track/2+self.overdev),
             (pcb_gap+bond_length, -pcb_gap-pcb_track/2+self.overdev),
             (pcb_gap/2+self.overdev, -pcb_gap-pcb_track/2+self.overdev)]

    gap_entity = self.polyline(points, layer=layer_GAP, name=name+'_gap')

    if self.is_mask:
        points =[(pcb_gap/2-self.gap_mask, pcb_gap+pcb_track/2+self.gap_mask),
                  (pcb_gap+bond_length, pcb_gap+pcb_track/2+self.gap_mask),
                  (pcb_gap+bond_length+adaptDist, gap+track/2+self.gap_mask),
                  (pcb_gap+bond_length+adaptDist, -gap-self.gap_mask),
                  (pcb_gap+bond_length, (pcb_gap)+(track-pcb_track)*0.5-self.gap_mask),
                  (pcb_gap/2-self.gap_mask, (pcb_gap)+(track-pcb_track)*0.5-self.gap_mask)]

        mask_entity = self.polyline(points, layer=layer_MASK,
                                    name=name+"_mask")

    with self([adaptDist+pcb_gap+bond_length,0], [1,0]):
        portOut, = create_port(self, widths=[track+2*self.overdev,
                                             2*gap+track-2*self.overdev],
                               name=name)

    if tr_line:
        ohm = self.rect([pcb_gap/2+self.overdev, pcb_track/2+self.overdev],
                        [pcb_gap/2-2*self.overdev, -pcb_track-2*self.overdev],
                        layer=layer_RLC, name=name+'_ohm')
        points = [(pcb_gap/2+self.overdev, 0), (pcb_gap-self.overdev, 0)]
        ohm.assign_lumped_RLC(points, ('50ohm', 0, 0))
        self.polyline(points, name=name+'_line', closed=False, layer=layer_Default)

        ohm.assign_mesh_length(pcb_track/10)

    return [portOut]

def draw_quarter_circle(self, name, layer, fillet):
    '''
    Subtract a rectangle and a filleted square of size 'fillet'
    Input :
        name : (str) should be unique
        layer : (str) in caps_lock
        fillet : (int) gives the size of the square
    eps is necessary to avoid a bug of hfss
    '''

    temp = self.rect_corner_2D([0,0], [2*fillet,2*fillet], name=name ,layer=layer)
    temp_fillet = self.rect_corner_2D([0,0], [2*fillet,2*fillet], name=name+'_fillet', layer=layer)

    self._fillet(fillet-eps, [0], temp_fillet)

    self.subtract(temp, [temp_fillet])

def cutout(self, name, zone_size):
    '''Create a mask of size 'zone_size'
    '''
    zone_size = parse_entry(zone_size)
    cutout_rect = self.rect_center_2D([0, 0], zone_size, name=name, layer=layer_MASK)
    #self.maskObjects.append(cutout_rect)
    return [[], [cutout_rect]]

def draw_T(self, name, iTrack, iGap):
    if not self.is_overdev or self.val(self.overdev<0):
        cutout = self.rect_center_2D([0,self.overdev/2], [2*iGap+iTrack, 2*iGap+iTrack-self.overdev], name=name+'_cutout', layer=layer_GAP)
        self.gapObjects.append(cutout)
    else:
        points = [       (-(iGap+iTrack/2),-iTrack/2-iGap+self.overdev),
                         (-(iGap+iTrack/2), iGap-self.overdev),
                         ((iGap+iTrack/2), iGap-self.overdev),
                         ((iGap+iTrack/2), -(iGap+iTrack)+self.overdev),
                         ((iGap+iTrack/2)-self.overdev, -(iGap+iTrack)+self.overdev),
                         ((iGap+iTrack/2)-self.overdev, -(iGap+iTrack)),
                         (-iTrack/2-iGap+self.overdev, -(iGap+iTrack)),
                         (-iTrack/2-iGap+self.overdev, self.overdev-(iGap+iTrack)) ]

        cutout = self.polyline_2D(points, name=name+'_cutout', layer=layer_GAP)
        self.gapObjects.append(cutout)

    if self.is_mask:
        mask = self.rect_center_2D([-iGap-iTrack/2,-iGap-iTrack/2], [2*iGap+iTrack, 2*iGap+iTrack+self.gap_mask], name = name+'_mask', layer=layer_MASK)
        self.maskObjects.append(mask)

    points = [                   (-(iGap+iTrack/2),-iTrack/2-self.overdev),
                                 (-(iGap+iTrack/2), iTrack/2+self.overdev),
                                 ((iGap+iTrack/2), iTrack/2+self.overdev),
                                 ((iGap+iTrack/2), -iTrack/2-self.overdev),
                                 (iTrack/2+self.overdev, -iTrack/2-self.overdev),
                                 (iTrack/2+self.overdev, -iGap-iTrack/2),
                                 (-iTrack/2-self.overdev, -iGap-iTrack/2),
                                 (-iTrack/2-self.overdev, -iTrack/2-self.overdev)]
    track = self.polyline_2D(points, name = name+'_track', layer=layer_TRACK)
    if iGap<iTrack:
        #not sure if self.val(iGap)<self.val(iTrack) was correct
        fillet=iGap
    else:
        fillet=iTrack
    self._fillet(fillet-eps,[4,7], track)

    self.trackObjects.append(track)

    portOut1 = self.port('portOut1', [iTrack/2+iGap, 0], [1,0], iTrack+2*self.overdev, iGap-2*self.overdev)
    #ports[name+'_1'] = portOut1
    portOut2 = self.port('portOut2', [-(iTrack/2+iGap), 0], [-1,0], iTrack+2*self.overdev, iGap-2*self.overdev)
    #ports[name+'_2'] = portOut2
    portOut3 = self.port('portOut2', [0, -(iTrack/2+iGap)], [0,-1], iTrack+2*self.overdev, iGap-2*self.overdev)
    #ports[name+'_3'] = portOut3

    return [[portOut1,portOut2,portOut3], [track, cutout]]

def draw_end_cable(self, name, iTrack, iGap, typeEnd = 'open', fillet=None):
    iTrack, iGap = parse_entry(iTrack, iGap)
    track, mask = None, None # track is not created in every cases

    if typeEnd=='open' or typeEnd=='Open':
        cutout = self.rect_center_2D([iGap,-(iTrack+2*iGap)/2+self.overdev], [-iGap+self.overdev, iTrack+2*iGap-2*self.overdev], name=name+'_cutout', layer=layer_GAP)
        if fillet is not None:
            cutout.fillet(iGap-self.overdev-eps,[2,1])

        self.gapObjects.append(cutout)
        portOut = self.port('portOut'+name, [iGap, 0], [1,0], iTrack+2*self.overdev, iGap-2*self.overdev)

        if self.is_overdev:
            track = self.rect_center_2D([iGap,-iTrack/2-self.overdev], [-self.overdev, iTrack+2*self.overdev], name=name+'_track' ,layer=layer_TRACK)
            self.trackObjects.append(track)
        if self.is_mask:
            mask = self.rect_center_2D([-self.gap_mask,-(iTrack+2*iGap)/2-self.gap_mask],[iGap+self.gap_mask, iTrack+2*iGap+2*self.gap_mask],name=name+'_mask', layer=layer_MASK)
            if fillet is not None:
                mask.fillet(iGap+self.gap_mask-eps,[0,3])

            self.maskObjects.append(mask)

    elif typeEnd=='short' or typeEnd=='Short':
        cutout1 = self.rect_center_2D([iGap/2,-(iTrack/2+iGap)+self.overdev], [-iGap/2+self.overdev, iGap-2*self.overdev], name=name+'_cutout1', layer=layer_GAP)
        cutout2 = self.rect_center_2D([iGap/2,(iTrack/2+iGap)-self.overdev], [-iGap/2+self.overdev, -iGap+2*self.overdev], name=name+'_cutout2', layer=layer_GAP)
        if fillet is not None:
            cutout1.fillet(iGap/2-self.overdev-eps,[2,1])
            cutout2.fillet(iGap/2-self.overdev-eps,[2,1])

        cutout = self.unite([cutout1, cutout2], name+'_cutout')
        self.gapObjects.append(cutout)
        portOut = self.port(name+"portOut", [iGap/2, 0], [1,0], iTrack+2*self.overdev, iGap-2*self.overdev)

        if self.is_mask:
            mask = self.rect_center_2D([-self.gap_mask,-(iTrack+2*iGap)/2-self.gap_mask], [iGap/2+self.gap_mask, iTrack+2*iGap+2*self.gap_mask], name=name+'_mask', layer=layer_MASK)
            if fillet is not None:
                mask.fillet(iGap/2+self.gap_mask-eps,[0,3])

            self.maskObjects.append(mask)

    else:
        raise ValueError("typeEnd should be 'open' or 'short', given %s" % typeEnd)

    return [[portOut], [track, cutout, mask]]



def size_dc_gap(self, length, positions, widths, border):
    # Ne pas s'en préoccuper
    length, positions, widths, border = parse_entry(length, positions, widths, border)

    low = np.argmin(positions)
    high = np.argmax(positions)
    pos_cutout = [-length/2, positions[low]-widths[low]/2-border]
    width_cutout = positions[high]-positions[low]+widths[high]/2+widths[low]/2+2*border
    vec_cutout = [length, width_cutout]

    return pos_cutout, width_cutout, vec_cutout


def cavity_3D(self, name, cylinder_radius, cylinder_height, antenna_radius, antenna_height):
    '''
    Draws a 3D vacuum cylinder (z axis) with an antenna. Assign PerfE to the surfaces
     _____
    (____() antenna of radius 'antenna_radius', and height 'antenna_height'
     __________
    /          /
    |          |cylinder of radius 'cylinder_radius' and height 'cylinder_height'
    \__________\

    '''
    outer_cylinder = self.cylinder_3D([0,0,0],
                                      cylinder_radius,
                                      cylinder_height,
                                      "Z",
                                      name=name+"_outer_cylinder",
                                      layer=layer_Default)

    antenna = self.cylinder_3D([0,0,0],
                               antenna_radius
                               ,antenna_height,
                               "Z",
                               name=name+"_antenna",
                               layer=layer_Default)

    outer_cylinder.subtract(antenna, keep_originals = True)

    antenna.assign_material("aluminum")
    antenna.assign_perfect_E(name+'_PerfE')
    outer_cylinder.assign_perfect_E(name+'_PerfE')

    return [[],[antenna]]

def cavity_3D_simple(self, name, radius, cylinder_height, antenna_radius, antenna_height, insert_radius, depth):

    radius, cylinder_height, antenna_radius, antenna_height, insert_radius, depth = parse_entry(radius, cylinder_height, antenna_radius, antenna_height, insert_radius, depth)

    cylinder = self.cylinder_3D([0,0,0],
                                radius,
                                cylinder_height,
                                "Z",
                                name=name+"_inner_cylinder",
                                layer=layer_Default)

    cylinder.assign_perfect_E(name+'_PerfE')

    antenna = self.cylinder_3D([0,0,0],
                               antenna_radius,
                               antenna_height,
                               "Z",
                               name=name+"_antenna",
                               layer=layer_Default)

    self.make_material(antenna, "\"aluminum\"")

    antenna.assign_perfect_E(name+'antenna_PerfE')

    cylinder_side = self.cylinder_3D([0,radius-depth,antenna_height],
                                     insert_radius,
                                     radius,
                                     "Y",
                                     name=name+"_insert",
                                     layer=layer_Default)

    cylinder.unite(cylinder_side)

    return [[],[cylinder, antenna]]

def cavity_3D_with_ports(self, name, cavity_param, transmons_param, ports_param):
    '''
    cavity_param = [rext,hext, rint, hint]
    ports_param = [[x, y, z, axis, param]...]
    transmons_param = [[x,y,z, axis, param]...]
    '''
    cavity_param, ports_param, transmons_param = parse_entry(cavity_param, ports_param, transmons_param)

    cavity = self.cylinder_3D([0,0,0],
                              cavity_param[0],
                              cavity_param[1],
                              "Z",
                              name=name+"_cavity",
                              layer=layer_Default)

    cavity.assign_perfect_E(name+'_PerfE')

    antenna = self.cylinder_3D([0,0,0],
                               cavity_param[2],
                               cavity_param[3],
                               "Z",
                               name=name+"_antenna",
                               layer=layer_Default)

    self.make_material(antenna, "\"aluminum\"")

    cavity.subtract(antenna)

    antenna.assign_perfect_E(name+'antenna_PerfE')

    cylinders = [cavity]

    to_subtract = []

    if ports_param!=None:
        for ii,port_param in enumerate(ports_param):
            angle = port_param[3]
            print(angle)
            self.set_coor(pos=port_param[:3], ori=angle)
            result = self.cable_3D(*port_param[4])
            cylinders.append(result[0])
            to_subtract.append(result[1])

    if transmons_param!=None:
        for ii,transmon_param in enumerate(transmons_param):
            angle = transmon_param[3]
#            angle = {"+X":0, "+Y":90, "-Y":-90}[axis]
            self.set_coor(pos=transmon_param[:3], ori=angle)
            cylinders.append(self.draw_cylinder_transmon(*transmon_param[4]))


    union = self.unite(cylinders, "main_obj")
    if to_subtract !=None:
        self.subtract(union, to_subtract)
    return union

def cable_3D(self, name, r_gaine, r_dielec, r_ame, L_cable, L_connector, axis):

    """
    TODO: Add a clear description of what this function actually draws.
    """

    r_gaine, r_ame, r_dielec, L_cable, L_connector, axis = parse_entry(r_gaine, r_ame, r_dielec, L_cable, L_connector, axis)

    ame = self.cylinder_3D([0,0,0],
                           r_ame,
                           L_cable,
                           axis,
                           layer=layer_Default,
                           name=name+'ame')
    creux = self.cylinder_3D([0,0,0],
                             r_ame,
                             L_cable,
                             axis,
                             layer=layer_Default,
                             name=name+'creux')
    dielec = self.cylinder_3D([0,0,0],
                              r_dielec,
                              L_cable,
                              axis,
                              layer=layer_Default,
                              name=name+'dielectric')

    dielec.subtract(creux, keep_originals=True)

    creux1 = self.cylinder_3D([0,0,0],
                              r_dielec,
                              L_cable,
                              axis,
                              layer=layer_Default,
                              name=name+'creux1')
    gaine = self.cylinder_3D([0,0,0],
                             r_gaine,
                             L_cable,
                             axis,
                             layer=layer_Default,
                             name=name+'gaine')
    creux.subtract(creux1, keep_originals=False)
    dielec.assign_material("Teflon (tm)")

    creux2 = self.cylinder_3D([0,0,L_cable],
                              r_ame,
                              L_connector,
                              axis,
                              layer=layer_Default,
                              name=name+'creux2')
    ame_probe = self.cylinder_3D([0,0,L_cable],
                                 r_ame,
                                 L_connector,
                                 axis,
                                 layer=layer_Default,
                                 name=name+'ame_probe')
    gaine_probe = self.cylinder_3D([0,0,L_cable],
                                   r_gaine,
                                   L_connector,
                                   axis,
                                   layer=layer_Default,
                                   name = name+'gaine_probe')
    gaine_probe.subtract(creux2, keep_originals=False)

    creux.delete()

    ame.assign_material("copper")
    ame_probe.assign_material("copper")
    gaine.assign_material("perfect conductor")
    gaine_probe.assign_material("perfect conductor")

    return gaine_probe, ame_probe

def insert_transmon(self, name, cutout_size, pad_spacing, pad_size, Jwidth, track, gap, Jinduc):
    cutout_size, pad_spacing, pad_size, Jwidth, track, gap, Jinduc = parse_entry(cutout_size, pad_spacing, pad_size, Jwidth, track, gap, Jinduc)
    self.set_coor(pos = ['0mm', '0mm','0mm'], ori=[1,0])
    L1 = self.draw_cavity_transmon('cavity_TRM', cutout_size[:2], pad_spacing, pad_size, Jwidth, track, gap, Jinduc)
    self.make_rlc_boundary(*L1)
    box = self.box_center([0,0,-cutout_size[2]/2], cutout_size, layer=layer_Default, name=name+"transmon_box")
    self.make_material(box, "\"sapphire\"")

def draw_alignement_mark(self, name, iSize, iXdist, iYdist):
        iXdist, iYdist, iSize=parse_entry(iXdist, iYdist, iSize)
        raw_points = [(iXdist,iYdist),
                      (iSize/2,iSize/2),
                      (-iSize,0)]
        mark1=self.polyline_2D(self.append_points(raw_points), name=name+"_mark_a", layer=layer_TRACK )

        raw_points = [(iXdist,iYdist),
                              (-iSize/2,-iSize/2),
                              (iSize,0)]
        mark2=self.polyline_2D(self.append_points(raw_points), name=name+"_mark_b", layer=layer_TRACK )
        self.gapObjects.append(self.unite([mark1,mark2]))

def draw_alignement_mark_r(self, name, size, disp, suff=''):
    size, disp = parse_entry(size, disp)
    raw_points = [(*disp,),
                  (size/2,size/2),
                  (0,-size)]
    marks = []
    marks.append(self.polyline_2D(self.append_points(raw_points), name=name+'_'+suff+"a", layer=layer_TRACK ))
    marks.append(self.polyline_2D(self.append_points(self.refy_points(raw_points, disp[0])), name=name+'_'+suff+"b", layer=layer_TRACK))
    self.gapObjects.append(self.unite(marks, name=name+'union_gap'+suff))
    if self.is_mask:
        raw_points_mask = [(disp[0]-self.gap_mask,disp[1]),
                           (size/2+2*self.gap_mask,size/2+self.gap_mask*2),
                           (0,-size-self.gap_mask*4)]
        marks_mask = []
        marks_mask.append(self.polyline_2D(self.append_points(raw_points_mask), name=name+"_mask_a", layer=layer_TRACK ))
        marks_mask.append(self.polyline_2D(self.append_points(self.refy_points(raw_points_mask, disp[0])), name=name+'_mask_b', layer=layer_TRACK))
        self.maskObjects.append(self.unite(marks_mask, name=name+'union_mask'+suff))

def draw_alignement_marks(self, name, size, disp, dict_except=None):
    size, disp = parse_entry(size, disp)
    disp = Vector(disp)
    moves = []
    directions_name = ['NE', 'NO', 'SE', 'SO']
    directions_exp = [[1,1], [-1,1], [1,-1], [-1,-1]]
    if dict_except is not None:
        for direction_name in directions_name:
            try:
                moves.append(parse_entry(dict_except[direction_name]))
            except Exception:
                moves.append([0,0])
    else:
        moves = [[0,0] for ii in range(4)]

    for move, direction_exp, direction_name in zip(moves, directions_exp, directions_name):
        self.draw_alignement_mark_r(name, size, disp*direction_exp+move, suff=direction_name)

def draw_dose_test(self, name, pad_size, pad_spacing, iTrack, bridge, N, bridge_spacing, length_big_junction, length_small_junction):
    pad_size, pad_spacing, iTrack, bridge, bridge_spacing, length_big_junction, length_small_junction = parse_entry(pad_size, pad_spacing, iTrack, bridge, bridge_spacing, length_big_junction, length_small_junction)
    pad_size = Vector(pad_size)
    self.rect_corner_2D([-pad_spacing/2, -pad_size[1]/2], [-pad_size[0],pad_size[1]], name=name+'_left', layer=layer_TRACK)
    self.rect_corner_2D([pad_spacing/2, pad_size[1]/2], [pad_size[0],-pad_size[1]], name=name+'_right', layer=layer_TRACK)
    portOut1 = self.port(name+"_portOut1", [pad_spacing/2, 0], [-1,0], iTrack, 0)
    portOut2 = self.port(name+"_portOut2", [-pad_spacing/2, 0], [1,0], iTrack, 0)

    snail_track = self._connect_snails2(name+'_junction', name+"_portOut1", name+"_portOut2", [20e-6,20e-6], length_big_junction, 3, length_small_junction, 1, N, bridge, bridge_spacing)#(squid_size, width_top, n_top, width_bot, n_bot, N, width_bridge)
    return snail_track

def draw_dose_test_junction(self, name, pad_size, pad_spacing, width, width_bridge, n_bridge=1, spacing_bridge=0, alternate_width=True, version=0):
        pad_size, pad_spacing, width, spacing_bridge, width_bridge = parse_entry(pad_size, pad_spacing, width, spacing_bridge, width_bridge)
        pad_size = Vector(pad_size)
        if self.val(width) < 1.5e-6 and n_bridge==1:
            width_jct = width
            width = 1.5e-6
        else:
            width_jct=None

        self.rect_corner_2D([-pad_spacing/2, -pad_size[1]/2], [-pad_size[0],pad_size[1]], name=name+'_left', layer =layer_TRACK)
        self.rect_corner_2D([pad_spacing/2, pad_size[1]/2], [pad_size[0],-pad_size[1]], name=name+'_right', layer=layer_TRACK)

        portOut1 = self.port(name+"_portOut1", [pad_spacing/2-pad_size[0]/2, 0], [-1,0], width, 0)
        portOut2 = self.port(name+"_portOut2", [-pad_spacing/2+pad_size[0]/2, 0], [1,0], width, 0)

#        jcts = self.connect_elt(name+'_junction', name+'_2', name+'_1')
        if alternate_width:
            if version==0:
                self._connect_jct(name+"connect_alternate", name+"_portOut1", name+"_portOut2", width_bridge, n=n_bridge, spacing_bridge=spacing_bridge, width_jct=width_jct)
            elif version==1:
                self._connect_jct(name+"connect_alternate", name+"_portOut1", name+"_portOut2", width_bridge, n=n_bridge, spacing_bridge=spacing_bridge, width_jct=width_jct, thin=True)
        else:
            if version==0:
                self._connect_jct(name+"connect", name+"_portOut1", name+"_portOut2", width_bridge, n=n_bridge, spacing_bridge=spacing_bridge, assymetry=0, width_jct=width_jct)
            elif version==1:
                self._connect_jct(name+"connect", name+"_portOut1", name+"_portOut2", width_bridge, n=n_bridge, spacing_bridge=spacing_bridge, assymetry=0, width_jct=width_jct, thin=True)

def draw_selfparity(self,
                    name,
                    cutout_size,
                    cap_depth,
                    ind_gap,
                    jn_gap,
                    buffer,
                    track_left,
                    gap_left,
                    track_right,
                    gap_right,
                    track,
                    fillet=None):

    parsed = parse_entry(name,
                         cutout_size,
                         cap_depth,
                         ind_gap,
                         jn_gap,
                         buffer,
                         track_left,
                         gap_left,
                         track_right,
                         track,
                         gap_right)

    (name,
     cutout_size,
     cap_depth,
     ind_gap,
     jn_gap,
     buffer,
     track_left,
     gap_left,
     track_right,
     track,
     gap_right) = parsed

    cutout_size = Vector(cutout_size)

    cutout = self.rect_center_2D([0,0], cutout_size, name=name+'_cutout', layer=14)
    if not self.is_litho:
        mesh = self.rect_center_2D([0,0], cutout_size, name=name+"_mesh", layer=layer_MESH)
        self.mesh_zone(mesh, '4um')
    if self.is_mask:
        mask = self.rect_center_2D([0,0], cutout_size+2*Vector([self.gap_mask,self.gap_mask]), name=name+'_mask', layer=layer_MASK)
        self.maskObjects.append(mask)
    self.gapObjects.append(cutout)

    left_track_raw_points = [(-cutout_size[0]/2+buffer-track/2-self.overdev, -ind_gap/2+self.overdev),
                             (track+2*self.overdev, 0),
                             (0, -buffer+track/2),
                             (buffer-track/2, 0),
                             (0, -track-2*self.overdev),
                             (-2*buffer-2*self.overdev, 0),
                             (0, track_left+2*self.overdev),
                             (buffer-track/2, 0)]
    left_track = self.polyline_2D(self.append_points(left_track_raw_points), name=name+"_track1", layer=13)

    right_track_raw_points = [(-cutout_size[0]/2+buffer-track/2-self.overdev, ind_gap/2-self.overdev),
                              (track+2*self.overdev, 0),
                              (0, buffer-track/2),
                              (buffer-track/2, 0),
                              (0, track+2*self.overdev),
                              (-2*buffer-2*self.overdev, 0),
                              (0, -track_right-2*self.overdev),
                              (buffer-track/2, 0)]
    right_track = self.polyline_2D(self.append_points(right_track_raw_points), name=name+"_track2", layer=13)

    left_elbow_raw_points = [(-cutout_size[0]/2+2*buffer+cap_depth+self.overdev, -ind_gap/2-buffer+track/2+self.overdev),
                             (buffer-track/2, 0),
                             (0, buffer-track/2+(ind_gap-jn_gap)/2),
                             (track+2*self.overdev, 0),
                             (0, -buffer-track/2-(ind_gap-jn_gap)/2-2*self.overdev),
                             (-buffer-track/2-2*self.overdev, 0)]
    left_elbow = self.polyline_2D(self.append_points(left_elbow_raw_points), name=name+"_elbow1", layer=13)

    right_elbow_raw_points = [(-cutout_size[0]/2+2*buffer+cap_depth+self.overdev, ind_gap/2+buffer-track/2-self.overdev),
                             (buffer-track/2, 0),
                             (0, -buffer+track/2-(ind_gap-jn_gap)/2),
                             (track+2*self.overdev, 0),
                             (0, buffer+track/2+(ind_gap-jn_gap)/2+2*self.overdev),
                             (-buffer-track/2-2*self.overdev, 0)]
    right_elbow = self.polyline_2D(self.append_points(right_elbow_raw_points), name=name+"_elbow2", layer=13)

    to_unite = [right_track, left_track, right_elbow, left_elbow]
    pads = self.unite(to_unite, name=name+'_pads')

    portOut1 = self.port(name+'_portOut1', [-cutout_size[0]/2, ind_gap/2+buffer+track/2-track_right/2], [-1,0], track_right+2*self.overdev, gap_right-2*self.overdev)
#        self.ports[name+'_1'] = portOut1
    portOut2 = self.port(name+'_portOut2', [-cutout_size[0]/2, -ind_gap/2-buffer-track/2+track_left/2], [-1,0], track_left+2*self.overdev, gap_left-2*self.overdev)
#        self.ports[name+'_2'] = portOut2

def draw_cos2phi(self, name, pad_size, pad_spacing, width, width_bridge,
                        loop_size, num_junctions, spacing_bridge=0):
    pad_size, pad_spacing, width, spacing_bridge, width_bridge, loop_size = parse_entry(pad_size, pad_spacing, width, spacing_bridge, width_bridge, loop_size)
    pad_size = Vector(pad_size)

    # connection pads
    self.rect_corner_2D([-pad_size[0]/2, pad_spacing/2], [pad_size[0],pad_size[1]], name=name+'_left', layer=layer_TRACK)
    self.rect_corner_2D([-pad_size[0]/2, -pad_spacing/2], [pad_size[0],-pad_size[1]], name=name+'_right', layer=12)

    r1 = Vector([1,0]).rot(Vector([0,-1]))

    for way in [-1, +1]:
        # small junctions
        self.port(name+'_1'+str(way+1), [way*0.5*loop_size[0], 5*width[1]], r1, width[1], 0)
        self.port(name+'_2'+str(way+1), [way*0.5*loop_size[0], -5*width[1]], -r1, width[1], 0)
        self._connect_array(name+'_jn', name+'_1'+str(way+1), name+'_2'+str(way+1), width_bridge, spacing_bridge)

        # long arrays
        self.port(name+'_3'+str(way+1), [way*0.5*loop_size[0], 0.5*loop_size[1]], r1, width[0], 0)
        self.port(name+'_4'+str(way+1), [way*0.5*loop_size[0], -0.5*loop_size[1]], -r1, width[0], 0)
        self._connect_array(name+'_array1'+str(way+1), name+'_3'+str(way+1), name+'_1'+str(way+1), width_bridge, spacing_bridge, n=num_junctions[0]/2)
        self._connect_array(name+'_array2'+str(way+1), name+'_4'+str(way+1), name+'_2'+str(way+1), width_bridge, spacing_bridge, n=num_junctions[0]/2)

        # first short arrays
        self.port(name+'_5'+str(way+1), [0.6*way*0.5*loop_size[0], 0.5*loop_size[1]], r1, width[0], 0)
        self.port(name+'_6'+str(way+1), [0.6*way*0.5*loop_size[0], -0.5*loop_size[1]], -r1, width[0], 0)
        self.port(name+'_7'+str(way+1), [0.6*way*0.5*loop_size[0], 3/8*0.5*loop_size[1]], r1, width[0], 0)
        self.port(name+'_8'+str(way+1), [0.6*way*0.5*loop_size[0], -3/8*0.5*loop_size[1]], -r1, width[0], 0)
        self._connect_array(name+'_array3'+str(way+1), name+'_5'+str(way+1), name+'_7'+str(way+1), width_bridge, spacing_bridge, n=num_junctions[1]/2)
        self._connect_array(name+'_array4'+str(way+1), name+'_6'+str(way+1), name+'_8'+str(way+1), width_bridge, spacing_bridge, n=num_junctions[1]/2)

        # second short arrays
        self.port(name+'_9'+str(way+1), [0.2*way*0.5*loop_size[0], 0.5*loop_size[1]], r1, width[0], 0)
        self.port(name+'_10'+str(way+1), [0.2*way*0.5*loop_size[0], -0.5*loop_size[1]], -r1, width[0], 0)
        self.port(name+'_11'+str(way+1), [0.2*way*0.5*loop_size[0], 3/8*0.5*loop_size[1]], r1, width[0], 0)
        self.port(name+'_12'+str(way+1), [0.2*way*0.5*loop_size[0], -3/8*0.5*loop_size[1]], -r1, width[0], 0)
        self._connect_array(name+'_array5'+str(way+1), name+'_9'+str(way+1), name+'_11'+str(way+1), width_bridge, spacing_bridge, n=num_junctions[1]/2)
        self._connect_array(name+'_array6'+str(way+1), name+'_10'+str(way+1), name+'_12'+str(way+1), width_bridge, spacing_bridge, n=num_junctions[1]/2)

        # vertical rectangles
        self.rect_corner_2D([-0.5*width[0], way*0.5*loop_size[1]], [width[0], way*0.5*(pad_spacing-loop_size[1])], name=name+'_56'+str(way+1), layer=layer_TRACK)

        # horizontal crossbars
        self.rect_corner_2D([-0.5*(width[0]+0.2*loop_size[0]), way*0.5*(loop_size[1]-width[0])], [0.2*loop_size[0]+width[0], way*width[0]], name=name+'rec5'+str(way+1), layer=11)
        self.rect_corner_2D([-0.5*(width[0]+1.0*loop_size[0]), way*0.5*(loop_size[1]-width[0])], [0.2*loop_size[0]+width[0], way*width[0]], name=name+'rec6'+str(way+1), layer=11)
        self.rect_corner_2D([-0.5*(width[0]-0.6*loop_size[0]), way*0.5*(loop_size[1]-width[0])], [0.2*loop_size[0]+width[0], way*width[0]], name=name+'rec7'+str(way+1), layer=11)
        self.rect_corner_2D([-0.5*(width[0]+0.6*loop_size[0]), way*0.5*(3/8*loop_size[1]-width[0])], [0.2*loop_size[0]+width[0], way*width[0]], name=name+'rec8'+str(way+1), layer=11)
        self.rect_corner_2D([-0.5*(width[0]-0.2*loop_size[0]), way*0.5*(3/8*loop_size[1]-width[0])], [0.2*loop_size[0]+width[0], way*width[0]], name=name+'rec9'+str(way+1), layer=11)

def draw_fluxline(self, name, iTrack, iGap, length, track_flux, slope=0.5, sym='center', return_spacing=0, return_depth=0, opposite=False):
    is_fillet=False
    iTrack, iGap, length, track_flux, return_spacing, return_depth = parse_entry(iTrack, iGap, length, track_flux, return_spacing, return_depth)
    if sym == 'center':
        offset_gap_down = 0
        offset_track_down = 0
        offset_gap_up = 0
        offset_track_up = 0
        adapt_length = (iTrack/2-track_flux)/slope
    else:
        adapt_length = (iTrack/2-track_flux+length/2)/slope
        if sym=='down':
                offset_gap_down = iGap+2*track_flux
                offset_track_down = length/2+track_flux
                offset_gap_up = 0
                offset_track_up = 0
        elif sym=='up':
            offset_gap_down = 0
            offset_track_down = 0
            offset_gap_up = iGap+2*track_flux
            offset_track_up = length/2+track_flux
        else:
            raise ValueError("sym should be either True, 'down' or 'up'.")

    points = [(adapt_length, iGap+iTrack/2),
              (adapt_length-self.gap_mask, iGap+iTrack/2),
              (track_flux/2, length/2+offset_gap_up),
              (track_flux/2, -length/2-offset_gap_down),
              (adapt_length-self.gap_mask, -(iGap+iTrack/2)),
              (adapt_length, -(iGap+iTrack/2))]


    if not sym == 'center':
        if return_spacing != 0:
            if not opposite:
                test1 = self.rect_corner_2D([return_depth, length/2+offset_gap_up], [-(return_spacing+track_flux/2+return_depth), return_spacing+track_flux], name=name+'_test1', layer=layer_GAP)
            else:
                test1 = self.rect_corner_2D([return_depth, -(length/2+offset_gap_up)], [-(return_spacing+track_flux/2+return_depth), -(return_spacing+track_flux)], name=name+'_test1', layer=layer_GAP)
            self.fillet(return_spacing+track_flux+eps, [2], test1)
            self.gapObjects.append(test1)



    gap = self.polyline_2D(points, name=name+'_gap', layer=layer_GAP)


    track = self.polyline_2D(points, closed=False, name=name+'_track', layer=layer_TRACK)
    gapext = self.polyline_2D(points, closed=False, name=name+'_gapext', layer=layer_GAP)
    fillet = eps
    fillet2 = track_flux+eps
    if is_fillet:
        self._fillet(fillet2, [1,4], track)
        self._fillet(fillet2, [1,4], gapext)
        self._fillet(fillet2,[1,4], gap)

        self._fillet(fillet, [3,4], track)
        self._fillet(fillet, [3,4], gapext)
        self._fillet(fillet, [3,4] ,gap)
#
#    points_starter = [(adapt_length, iGap+iTrack/2),
#                      (adapt_length, iGap+iTrack/2+track_flux)]

    points_starter = [(iGap+iTrack/2, adapt_length),
                      (iGap+iTrack/2+track_flux, adapt_length)]

    track_starter = self.polyline_2D(points_starter, closed=False, name=name+'_track1', layer=layer_TRACK)
    gapext_starter = self.polyline_2D(points_starter, closed=False, name=name+'_gapext1', layer=layer_GAP)


#    track = self._sweep_along_path(track_starter, track)
#    gapext = self._sweep_along_path(gapext_starter, gapext)
#
#    gap = self.unite([gap, gapext], name=gap.name+"2")

    if self.is_mask:
        mask = self.polyline_2D(points, name=name+'_mask', layer=layer_MASK)
        maskext = self.polyline_2D(points, closed=False, name=name+'_mask_ext_guide', layer=layer_MASK)
        points_starter_mask = [(adapt_length, iGap+iTrack/2),
                               (adapt_length, iGap+iTrack/2+self.gap_mask)]
        maskext_starter = self.polyline_2D(points_starter_mask, closed=False, name=name+'_maskext', layer=layer_MASK)
        maskext = self._sweep_along_path(maskext, maskext_starter)
        mask = self.unite([mask, maskext])
        self.maskObjects.append(mask)

    points = [(adapt_length, iTrack/2),
                                          (adapt_length-track_flux, iTrack/2),
                                          (track_flux/2, track_flux-offset_track_down+offset_track_up),
                                          (track_flux/2, -track_flux-offset_track_down+offset_track_up),
                                          (adapt_length-track_flux, -iTrack/2),
                                          (adapt_length, -iTrack/2)]

    track_adapt = self.polyline_2D(points, name=name+'_track_adapt', layer=layer_TRACK)
    if is_fillet:
        self._fillet(fillet2, [1,4], track_adapt)

#    track = self.unite([track, track_adapt], name=track.name+"track")
#            track.fillet(fillet, [15,20])
#            track.fillet(fillet2, [17,20])

    self.gapObjects.append(gap)
    self.trackObjects.append(track)

    portOut = self.port(name+'_outPort', [adapt_length, 0], [1,0], iTrack+2*self.overdev, iGap-2*self.overdev)
#    self.ports[name] = portOut