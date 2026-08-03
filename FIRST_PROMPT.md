Clearly, the planning stage requires back and forward interaction with the agent. However, this is a first prompt that I've used to get things started.

# First prompt

Foundry is an automation/resource management game, where you have to build a factory with different machines. Each machine can craft certain recipes to create higher level items. I would like you to create calculator in which the user can enter how much of a certain item they'd like to produce per minute (or do so for a combination of items). I'd like the calculator to then calculate and visualize what the required resources (per minute) are, and which factory buildings are needed to produce this amount. I'd like to show this for each intermediate step, i.e. show for each intermediate product how much of it needs to be produced per minute, and how many factory buildings are needed to produce this amount. This needs to be done until we use basic resources (ores, etc). Then, one step further is to also report the amount of ore that disappears from a vein - as this is not always the same as the amount of ore produced (see efficiency modifiers below).

You'll need to create a configuration file recipes.cfg that contains information on which recipes exist, in which factories they can be crafted, and at what rates.

Then, in the UI, the user not only needs to be able to configure the desired output product + rate, but if the factory in which this product is produced has multiple tiers (factory tiers essentialy modify the production speed, nothing else), they also need to be able to select which tier they are using for that type of factory type. Create a global switch for this, so that users can modify this in one go (if they've unlocked tier 2 assemblers, they will typically use tier 2 assemblers for everye step that requires an assembler). In addition, make modifiers so that they _can_ modify the tier used for individual recipes if it differs from the default they set through the global switch.

There are also other modifiers: robot workstations that are placed next to assemblers, which can modify the speed at which they work, or the efficiency. Efficiency works as follows: if a recipy for 2x product A + 2x product B = 1x product C has a 20% efficiency increase, that means that every 5 times the recipy is run, a free product C is produced. I.e. from 5 cycles, you get 6 products C, which costs a total of 10x products A and 10x product B. The rate at which the recipy produces is proportionally reduced, so it does not affect the speed at which the factory produces. I.e. if the factory produced 10x product C / min initially, it will still produce 10x product C / min if there is a 20% efficiency modifier. However, instead of costing 20x product A and 20x product B, it will now cost (20/1.2)x product A and (20/1.2)x product B. Effectively this means that while efficiency modifiers don't modify the output rate, they do modify the input rate of the ingredients. There are also speed modifiers. These simply increase the speed of a factory, without modifying the balance between the number of input/output items. I.e. a 20% speed increase in the above example would simply mean that produce C is produced at 12/min, i.e. 20% more than the original rate. Similarly, the inputs A and B will be consumed at 20*1.2=24 items/min. Efficiency modifiers on buildings that collect raw resources (e.g. miners that mine ore) simply mean that the amount of ore that is consumed from an ore patch is 20% lower (again, the speed stays constant). I.e. with a 20% efficiency modifier on an ore miner that produces 100 ore, only (100/1.2) or has disappeared from the ore patch. Please great global modifiers per type of building (e.g. Minder, Crusher, Smelter, Assembler, etc) so that the user does not have to configure too much. Then, make these overrideable for individual recipes, in case the user wants to deviate in specific cases.

A final modifier is that through research the efficiency with which ore and Olumite (the fundamental liquid resource) is mined can be increased. The user should be able to set this efficiency so that the rate at which ore is 'consumed' from the world (ore patches) is correctly calculated.

All factory types should be listed in factories.cfg. This configuration file should list the name of the factory, and for each factory which recipes they can produce, and what their power consumption is.

Finally, it should be displayed how much energy is consumed for producing the number of items. Note that factories that are idle don't consume any power.

An example of what the calculated should do, consider the following:
- A user puts in that they want create 20 / min of item A
- The recipy for item A is 5x item B + 10 x item C = 2x item A.
- The recipy is produced in tier 1 assemblers at 5 cycles/min, i.e. the base speed is 25x item B / min + 50x item C / min = 10x Item A / min.
- The recipy for item B is 5x item C + 2x item D = 5x Item B
- The rate for this recipy is that it is produced in tier 1 assemblers at 10 cycles/min, i.e. the base speed is 50x item C / min + 20x item D / min = 50x item B / min
- The user has configured that for assemblers, he has robot workstations that increase efficiency by 20%. This modifies the rates to (25/1.2)* item B / min + (50/1.2)* item C / min = 10 x Item A / min. For the first recipy. And it modifies to (50/1.2)* item C/min + (20/1.2) * item D / min = 50x item B / min.
- Let's assume produce C and D are basic product (for example: an ore). This means we break it down in one further step to show the ore consumed from the world by modifying it by the researched efficiency modifier.
- The user has configured a research efficiency modifier of 10%.
- Let's assume the assemblers use 550 kw each.

These are all the inputs. The calculator should then tell us the following:
- To produce the requested 20/min of item A, with the efficiency modifiers, I need 2 factories, and it takes (50/1.2) * item B / min + (100/1.2) * item C / min.
- To produce Item B at a rate of (100/1.2) / min, I need (100/1.2)/50 factories, and it takes (100/1.2)/1.2x item C / min, and (2/5)*(100/1.2)/1.2x item D / min.
- In total I need (2/5)*(100/1.2)/1.2x item D / min and ((100/1.2)/1.2x + (100/1.2)) Item C / min in terms of raw resources.

Essentially, in the backend, this should create a graph-like structure. The nodes being a (set of) factories with a particular recipy configured, and the arrows being the amount of input / output material going into and out of that node. In the GUI, I'd like to have multiple views. One showing the graph as nodes and arrows. The other showing just the total item/min counts for each item involved in the production chain, as well as total number of factories with a given recipy.

In terms of implementation: please implement this as a web page that I can serve locally. You can pick any web framework or langauge that you consider the most suitable for a project like this. Create an INSTALLTION.md file containing installation instructions, including a clear list of dependencies. Please make sure this can be hosted on a linux machine, and that tools needed to serve this page can be installed without having root access (i.e. with an unprivelidged user). Then, provide instructions on how to locally start the web server and access the required page.

Make sure that you create an API to bypass the user interface, and use this API to create unit tests for a few simple cases. This will allow me to check those simple cases for correctness at the end of the project, so that I know your implementation is correct.
