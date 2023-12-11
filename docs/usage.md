(usage)=

# Usage

Assuming that you've followed the {ref}`installations steps <installation>`, you're now ready to use this package.

Start by importing it:

```python
import aiohappyeyeballs

addr_infos = await loop.getaddrinfo("example.org", 80)

socket = await aiohappyeyeballs.start_connection(addr_infos)
socket = await aiohappyeyeballs.start_connection(addr_infos, local_addr_infos=local_addr_infos, happy_eyeballs_delay=0.2)

transport, protocol = await loop.create_connection(
    MyProtocol, sock=socket, ...)

# Remove the first address for each family from addr_info
aiohappyeyeballs.pop_addr_infos_interleave(addr_info, 1)

# Remove all matching address from addr_info
aiohappyeyeballs.remove_addr_infos(addr_info, "dead::beef::")

# Convert a local_addr to local_addr_infos
local_addr_infos = addr_to_addr_infos(("127.0.0.1",0))
```
