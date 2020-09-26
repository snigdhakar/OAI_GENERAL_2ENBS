#!/usr/bin/env python

#
# Standard geni-lib/portal libraries
#
import geni.portal as portal
import geni.rspec.pg as rspec
import geni.rspec.emulab as elab
import geni.rspec.igext as IG
import geni.urn as URN


tourDescription = """
Use this profile to instantiate an experiment using Open Air Interface
to realize an end-to-end LTE mobile network. The profile supports two
variants: (i) a simulated RAN (UE and eNodeB) connected to an EPC, or
(ii) an OTS UE (Nexus 5) connected to an SDR-based eNodeB via a
controlled RF attenuator and connected to an EPC.

The simulated version of the profile uses the following resources:

  * A d430 compute node running the OAI simulated UE and eNodeB ('sim-enb') 
  * A d430 compute node running the OAI EPC (HSS, MME, SPGW) ('epc')

The OTS UE/SDR-based eNodeB version of the profile includes
the following resources:

  * Off-the-shelf Nexus 5 UE running Android 4.4.4 KitKat ('rue1')
  * SDR eNodeB (Intel NUC + USRP B210) running OAI eNodeB ('enb1')
  * A d430 compute node running the OAI EPC (HSS, MME, SPGW) ('epc')
  * A d430 compute node providing out-of-band ADB access to the UE ('adb-tgt')

Startup scripts automatically configure OAI for the specific allocated resources.

For more detailed information:

  * [Getting Started](https://gitlab.flux.utah.edu/powder-profiles/OAI-GENERAL/blob/master/README.md)

""";

tourInstructions = """
After your experiment swapped in succesfully (i.e., is in the Ready state):

**For the version with simulated UE and eNodeB**

Log onto the `epc` node and run:

    sudo /local/repository/bin/start_oai.pl -r sim

This will start up the EPC services on the `epc`node *and* the
simulated UE/eNodeB on the `sim-enb` node.

Log onto the `sim-enb` to verify the functionality:

	ping -I oip1 8.8.8.8
	
You can also look at the output of the simulated UE/eNodeB process:

	sudo screen -r sim_enb

**For the version with OTS UE and SDR-based eNodeB**

Log onto the `enb1` node and start the eNodeB service:

	sudo /local/repository/bin/enb.start.sh
	
To view the output of the eNodeB:

	sudo screen -r enb


Log onto the `epc` node and start the EPC services:

	sudo /local/repository/bin/start_oai.pl
	
To log onto the UE (`rue1`), first log onto the `adb-tgt` node and start up the adb daemon:

	pnadb -a

Then (still on `adb-tgt`) get an ADB shell on the UE by running:

	adb shell
	
If the UE successfully connected you should be able to ping an address on
the Internet from the ADB shell, e.g.,

	ping 8.8.8.8
	
If the UE did not connect by itself, (i.e., you get a "Network is unreachable" error),
you might have to reboot the UE (by executing `adb reboot` from the `adb-tgt` node,
or by executing `reboot` directly in the ADB shell on the UE). And then repeating
the `pnadb -a` and `adb shell` commands to get back on the UE to test.


While OAI is still a system in development and may be unstable, you can usually recover
from any issue by running `start_oai.pl` to restart all the services.

  * [More details](https://gitlab.flux.utah.edu/powder-profiles/OAI-GENERAL/blob/master/README.md)

""";


#
# PhantomNet extensions.
#
import geni.rspec.emulab.pnext as PN

#
# Globals
#
class GLOBALS(object):
    OAI_DS = "urn:publicid:IDN+emulab.net:phantomnet+ltdataset+oai-develop"
    OAI_SIM_DS = "urn:publicid:IDN+emulab.net:phantomnet+dataset+PhantomNet:oai"
    UE_IMG  = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:ANDROID444-STD")
    ADB_IMG = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:UBUNTU14-64-PNTOOLS")
    OAI_EPC_IMG = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:UBUNTU16-64-OAIEPC")
    OAI_ENB_IMG = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:OAI-Real-Hardware.enb1")
    OAI_SIM_IMG = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:UBUNTU14-64-OAI")
    OAI_CONF_SCRIPT = "/usr/bin/sudo /local/repository/bin/config_oai.pl"
    NUC_HWTYPE = "nuc5300"
    UE_HWTYPE = "nexus5"

def connectOAI_DS(node, sim):
    # Create remote read-write clone dataset object bound to OAI dataset
    bs = request.RemoteBlockstore("ds-%s" % node.name, "/opt/oai")
    if sim == 1:
	bs.dataset = GLOBALS.OAI_SIM_DS
    else:
	bs.dataset = GLOBALS.OAI_DS
    bs.rwclone = True

    # Create link from node to OAI dataset rw clone
    node_if = node.addInterface("dsif_%s" % node.name)
    bslink = request.Link("dslink_%s" % node.name)
    bslink.addInterface(node_if)
    bslink.addInterface(bs.interface)
    bslink.vlan_tagging = True
    bslink.best_effort = True

#
# This geni-lib script is designed to run in the PhantomNet Portal.
#
pc = portal.Context()

#
# Profile parameters.
#

sim_hardware_types = ['d430','d740']

pc.defineParameter("TYPE", "Experiment type",
                   portal.ParameterType.STRING,"sim",[("sim","Simulated UE/eNodeB"),("atten","OTS UE with RF attenuator")],
                   longDescription="*Simulated RAN*: OAI simulated UE/eNodeB connected to an OAI EPC. *OTS UE/SDR-based eNodeB with RF attenuator connected to OAI EPC*: OTS UE (Nexus 5) connected to controllable RF attenuator matrix.")

pc.defineParameter("FIXED_UE", "Bind to a specific UE",
                   portal.ParameterType.STRING, "", advanced=True,
                   longDescription="Input the name of a POWDER controlled RF UE node to allocate (e.g., 'ue1').  Leave blank to let the mapping algorithm choose.")
pc.defineParameter("FIXED_ENB", "Bind to a specific eNodeB",
                   portal.ParameterType.STRING, "", advanced=True,
                   longDescription="Input the name of a POWDER controlled RF eNodeB device to allocate (e.g., 'nuc1').  Leave blank to let the mapping algorithm choose.  If you bind both UE and eNodeB devices, mapping will fail unless there is path between them via the attenuator matrix.")

pc.defineParameter("SIM_HWTYPE", "Compute hardware type to use (SIM mode only)",
                   portal.ParameterType.STRING, sim_hardware_types[0],
                   sim_hardware_types, advanced=True,
                   longDescription="Use this parameter if you would like to select a different hardware type to use FOR SIMULATED MODE.  The types in this list are known to work.")

params = pc.bindParameters()

#
# Give the library a chance to return nice JSON-formatted exception(s) and/or
# warnings; this might sys.exit().
#
pc.verifyParameters()

#
# Create our in-memory model of the RSpec -- the resources we're going
# to request in our experiment, and their configuration.
#
request = pc.makeRequestRSpec()
epclink1 = request.Link("s1-lan1")
epclink2 = request.Link("s1-lan2")

# Checking for oaisim

if params.TYPE == "sim":
    sim_enb = request.RawPC("sim-enb")
    sim_enb.disk_image = GLOBALS.OAI_SIM_IMG
    sim_enb.hardware_type = params.SIM_HWTYPE
    sim_enb.addService(rspec.Execute(shell="sh", command=GLOBALS.OAI_CONF_SCRIPT + " -r SIM_ENB"))
    connectOAI_DS(sim_enb, 1)
    epclink1.addNode(sim_enb)
else:
    # Add a node to act as the ADB target host
    adb_t = request.RawPC("adb-tgt")
    adb_t.disk_image = GLOBALS.ADB_IMG

    # Add a NUC eNB node.
    enb1 = request.RawPC("enb1")
    if params.FIXED_ENB:
        enb1.component_id = params.FIXED_ENB
    enb1.hardware_type = GLOBALS.NUC_HWTYPE
    enb1.disk_image = GLOBALS.OAI_ENB_IMG
    enb1.Desire( "rf-controlled", 1 )
    connectOAI_DS(enb1, 0)
    enb1.addService(rspec.Execute(shell="sh", command=GLOBALS.OAI_CONF_SCRIPT + " -r ENB"))
    enb1_rue1_rf = enb1.addInterface("rue1_rf")
	
	# Add another NUC eNB node.
    enb2 = request.RawPC("enb2")
    if params.FIXED_ENB:
        enb2.component_id = params.FIXED_ENB
    enb2.hardware_type = GLOBALS.NUC_HWTYPE
    enb2.disk_image = GLOBALS.OAI_ENB_IMG
    enb2.Desire( "rf-controlled", 1 )
    connectOAI_DS(enb2, 0)
    enb2.addService(rspec.Execute(shell="sh", command=GLOBALS.OAI_CONF_SCRIPT + " -r ENB"))
    enb2_rue1_rf = enb2.addInterface("rue1_rf")

    # Add an OTS (Nexus 5) UE
    rue1 = request.UE("rue1")
    if params.FIXED_UE:
        rue1.component_id = params.FIXED_UE
    rue1.hardware_type = GLOBALS.UE_HWTYPE
    rue1.disk_image = GLOBALS.UE_IMG
    rue1.Desire( "rf-controlled", 1 )    
    rue1.adb_target = "adb-tgt"
    rue1_enb1_rf = rue1.addInterface("enb1_rf")
	
    rue1_enb2_rf = rue1.addInterface("enb2_rf")

    # Create the RF link between the Nexus 5 UE and eNodeB
    rflink1 = request.RFLink("rflink1")
    rflink1.addInterface(enb1_rue1_rf)
    rflink1.addInterface(rue1_enb1_rf)
	
    rflink2 = request.RFLink("rflink2")
    rflink2.addInterface(enb2_rue1_rf)
    rflink2.addInterface(rue1_enb2_rf)

    # Add a link connecting the NUC eNB and the OAI EPC node.
    epclink1.addNode(enb1)
	
    epclink2.addNode(enb2)

# Add OAI EPC (HSS, MME, SPGW) node.
epc = request.RawPC("epc")
epc.disk_image = GLOBALS.OAI_EPC_IMG
epc.addService(rspec.Execute(shell="sh", command=GLOBALS.OAI_CONF_SCRIPT + " -r EPC"))
connectOAI_DS(epc, 0)
 
epclink1.addNode(epc)
epclink1.link_multiplexing = True
epclink1.vlan_tagging = True
epclink1.best_effort = True

epclink2.addNode(epc)
epclink2.link_multiplexing = True
epclink2.vlan_tagging = True
epclink2.best_effort = True

tour = IG.Tour()
tour.Description(IG.Tour.MARKDOWN, tourDescription)
tour.Instructions(IG.Tour.MARKDOWN, tourInstructions)
request.addTour(tour)

#
# Print and go!
#
pc.printRequestRSpec(request)
